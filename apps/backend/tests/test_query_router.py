import asyncio

from langchain_core.documents import Document

from app.infraestructure.llm import create_model, create_router_model
from app.services._multiquery_retriever import MultiqueryRetriever
from app.services.query_router import QueryRoute, QueryRouter
from app.settings import Settings


class FakeStructuredModel:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.invocations = []

    async def ainvoke(self, prompt_value, config=None):
        self.invocations.append(prompt_value)
        if self.error is not None:
            raise self.error
        return self.result


class FakeLLM:
    def __init__(self, structured_model):
        self.structured_model = structured_model
        self.structured_calls = []

    def with_structured_output(self, schema, **kwargs):
        self.structured_calls.append((schema, kwargs))
        return self.structured_model


class StubRouter:
    def __init__(self, route: QueryRoute):
        self._route = route
        self.calls = []

    async def route(self, question: str, history: str = "") -> QueryRoute:
        self.calls.append((question, history))
        return self._route


class StubQueryGenerator:
    def __init__(self, queries: list[str]):
        self._queries = queries
        self.calls = []

    async def generate_queries(self, question: str, history: str = "") -> list[str]:
        self.calls.append((question, history))
        return list(self._queries)


class RecordingVectorRetriever:
    def __init__(self, responses: list[list[tuple[Document, float]]]):
        self._responses = list(responses)
        self.calls: list[list[str]] = []

    async def retrieve_with_scores(self, queries):
        self.calls.append(list(queries))
        return self._responses.pop(0)

    async def enrich_documents(self, documents):
        return documents


def test_query_router_normalizes_structured_route():
    structured = FakeStructuredModel(
        result=QueryRoute(
            search_query="  dosis máxima de ibuprofeno en niños  ",
            medicines=[" Ibuprofeno ", "ibuprofeno", "  "],
            intent=" Maximum Dose ",
        )
    )
    llm = FakeLLM(structured)
    router = QueryRouter(model=llm)

    route = asyncio.run(
        router.route("¿Y en niños?", history="Usuario: dosis de ibuprofeno")
    )

    assert route == QueryRoute(
        search_query="dosis máxima de ibuprofeno en niños",
        medicines=["Ibuprofeno"],
        intent="maximum_dose",
    )
    assert llm.structured_calls == [(QueryRoute, {"method": "function_calling"})]


def test_query_router_replaces_snake_case_underscores_in_search_query():
    structured = FakeStructuredModel(
        result=QueryRoute(
            search_query="cual_es_la_dosis_maxima_de_paracetamol",
            medicines=["paracetamol"],
            intent="maximum_dose",
        )
    )
    router = QueryRouter(model=FakeLLM(structured))

    route = asyncio.run(router.route("¿Cuál es la dosis máxima de paracetamol?"))

    assert route.search_query == "cual es la dosis maxima de paracetamol"


def test_query_router_falls_back_to_original_question_on_error():
    llm = FakeLLM(FakeStructuredModel(error=RuntimeError("bedrock timeout")))
    router = QueryRouter(model=llm)

    route = asyncio.run(router.route("  dosis de paracetamol  "))

    assert route == QueryRoute(
        search_query="dosis de paracetamol",
        medicines=[],
        intent="general",
    )


def test_adaptive_retriever_runs_single_search_when_coverage_is_complete():
    router = StubRouter(
        QueryRoute(
            search_query="dosis máxima de ibuprofeno en niños",
            medicines=["ibuprofeno"],
            intent="maximum_dose",
        )
    )
    generator = StubQueryGenerator(["extra 1", "extra 2"])
    vector_retriever = RecordingVectorRetriever(
        responses=[
            [
                (Document(page_content="Ibuprofeno dosis máxima 1200 mg", metadata={"filename": "IBUPROFENO.pdf"}), 0.18),
                (Document(page_content="Posología de ibuprofeno en niños", metadata={"filename": "IBUPROFENO.pdf"}), 0.22),
                (Document(page_content="Advertencias de ibuprofeno", metadata={"filename": "IBUPROFENO.pdf"}), 0.29),
            ]
        ]
    )
    retriever = MultiqueryRetriever(
        vector_retriever=vector_retriever,
        query_router=router,
        queries_generator=generator,
        max_distance=0.7,
        min_results=3,
        max_results=10,
        expansion_max_queries=3,
    )

    docs = asyncio.run(retriever.ainvoke("¿Y en niños?", history="Usuario: ibuprofeno"))

    assert router.calls == [("¿Y en niños?", "Usuario: ibuprofeno")]
    assert vector_retriever.calls == [["dosis máxima de ibuprofeno en niños"]]
    assert generator.calls == []
    assert len(docs) == 3


def test_adaptive_retriever_expands_deterministically_for_missing_medicine():
    router = StubRouter(
        QueryRoute(
            search_query="dosis máxima de paracetamol e ibuprofeno",
            medicines=["paracetamol", "ibuprofeno"],
            intent="maximum_dose",
        )
    )
    generator = StubQueryGenerator(["unused llm query"])
    vector_retriever = RecordingVectorRetriever(
        responses=[
            [
                (Document(page_content="Paracetamol 500 mg dosis máxima", metadata={"filename": "PARACETAMOL.pdf"}), 0.19),
                (Document(page_content="Paracetamol posología adultos", metadata={"filename": "PARACETAMOL.pdf"}), 0.24),
                (Document(page_content="Paracetamol advertencias", metadata={"filename": "PARACETAMOL.pdf"}), 0.30),
            ],
            [
                (Document(page_content="Ibuprofeno dosis máxima diaria", metadata={"filename": "IBUPROFENO.pdf"}), 0.21),
            ],
        ]
    )
    retriever = MultiqueryRetriever(
        vector_retriever=vector_retriever,
        query_router=router,
        queries_generator=generator,
        max_distance=0.7,
        min_results=3,
        max_results=10,
        expansion_max_queries=3,
    )

    docs = asyncio.run(retriever.ainvoke("dosis máxima de paracetamol e ibuprofeno"))

    assert vector_retriever.calls == [
        ["dosis máxima de paracetamol e ibuprofeno"],
        ["ibuprofeno dosis máxima diaria posología"],
    ]
    assert generator.calls == []
    assert [doc.metadata["filename"] for doc in docs] == [
        "PARACETAMOL.pdf",
        "IBUPROFENO.pdf",
        "PARACETAMOL.pdf",
        "PARACETAMOL.pdf",
    ]


def test_adaptive_retriever_caps_low_coverage_expansion_to_one_round():
    router = StubRouter(
        QueryRoute(
            search_query="consulta ambigua",
            medicines=[],
            intent="general",
        )
    )
    generator = StubQueryGenerator(["alt 1", "alt 2", "alt 3", "alt 4"])
    vector_retriever = RecordingVectorRetriever(
        responses=[
            [(Document(page_content="solo un resultado"), 0.35)],
            [
                (Document(page_content="resultado extra 1"), 0.28),
                (Document(page_content="resultado extra 2"), 0.40),
            ],
        ]
    )
    retriever = MultiqueryRetriever(
        vector_retriever=vector_retriever,
        query_router=router,
        queries_generator=generator,
        max_distance=0.7,
        min_results=3,
        max_results=10,
        expansion_max_queries=2,
    )

    docs = asyncio.run(retriever.ainvoke("pregunta original"))

    assert vector_retriever.calls == [
        ["consulta ambigua"],
        ["alt 1", "alt 2"],
    ]
    assert len(generator.calls) == 1
    assert [doc.page_content for doc in docs] == [
        "resultado extra 1",
        "solo un resultado",
        "resultado extra 2",
    ]


def test_bedrock_chat_and_router_factories_use_configured_models(monkeypatch):
    captured = []

    class FakeChatBedrockConverse:
        def __init__(self, **kwargs):
            captured.append(kwargs)

    monkeypatch.setattr(
        "app.infraestructure.llm.ChatBedrockConverse",
        FakeChatBedrockConverse,
    )
    config = Settings(
        supabase_db_url="postgresql://example.test/db",
        chat_provider="bedrock",
        model_name="us.amazon.nova-lite-v1:0",
        router_provider="bedrock",
        router_model_name="us.amazon.nova-micro-v1:0",
        aws_region="us-east-2",
        groq_api_key=None,
    )

    create_model(config)
    create_router_model(config)

    assert captured == [
        {
            "model": "us.amazon.nova-lite-v1:0",
            "region_name": "us-east-2",
            "credentials_profile_name": None,
            "temperature": 0,
            "max_tokens": 4096,
        },
        {
            "model": "us.amazon.nova-micro-v1:0",
            "region_name": "us-east-2",
            "credentials_profile_name": None,
            "temperature": 0,
            "max_tokens": 256,
        },
    ]
