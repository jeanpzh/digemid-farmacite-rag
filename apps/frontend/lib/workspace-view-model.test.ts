import assert from "node:assert/strict";
import test from "node:test";

type WorkspaceViewModel = {
  getCitationDocumentType?: (filename: string) => string;
  getConsultationTitle?: (question?: string) => string;
};

async function loadWorkspaceViewModel(): Promise<WorkspaceViewModel> {
  try {
    return await import("./workspace-view-model");
  } catch {
    return {};
  }
}

test("builds a concise consultation title from a medicine question", async () => {
  const { getConsultationTitle } = await loadWorkspaceViewModel();

  assert.equal(typeof getConsultationTitle, "function");
  assert.equal(
    getConsultationTitle?.(
      "¿El ibuprofeno 200 mg está incluido como medicamento de venta sin receta?",
    ),
    "Ibuprofeno 200 mg",
  );
  assert.equal(
    getConsultationTitle?.("¿Qué precauciones tiene el clotrimazol 1%?"),
    "Clotrimazol 1%",
  );
  assert.equal(getConsultationTitle?.(), "Nueva consulta");
});

test("classifies citation filenames using available metadata", async () => {
  const { getCitationDocumentType } = await loadWorkspaceViewModel();

  assert.equal(typeof getCitationDocumentType, "function");
  assert.equal(
    getCitationDocumentType?.("IBUPROFENO_TabletaRecubierta.pdf"),
    "Ficha técnica",
  );
  assert.equal(
    getCitationDocumentType?.("IBUPROFENO_Inserto.pdf"),
    "Inserto",
  );
  assert.equal(
    getCitationDocumentType?.("IBUPROFENO_Rotulado.pdf"),
    "Rotulado",
  );
});
