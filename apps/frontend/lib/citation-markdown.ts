import { visitParents } from "unist-util-visit-parents";
import type { PhrasingContent, Root, Text } from "mdast";

const citationMarkerPattern = /\[(S\d+)\]/g;
const citationLinkPrefix = "#citation-";

export function citationLabelFromHref(href: unknown) {
  if (typeof href !== "string" || !href.startsWith(citationLinkPrefix)) {
    return null;
  }
  return href.slice(citationLinkPrefix.length);
}

export function citationRemarkPlugin(labels: ReadonlySet<string>) {
  return () => (tree: Root) => {
    visitParents(tree, "text", (node: Text, ancestors) => {
      const parent = ancestors.at(-1) as
        | { children: PhrasingContent[] }
        | undefined;
      const insideProtectedNode = ancestors.some(
        (ancestor) =>
          ancestor.type === "link" || ancestor.type === "linkReference",
      );
      if (insideProtectedNode || !parent) {
        return;
      }

      const index = parent.children.indexOf(node);
      if (index < 0) {
        return;
      }

      const replacements: PhrasingContent[] = [];
      let cursor = 0;
      for (const match of node.value.matchAll(citationMarkerPattern)) {
        const label = match[1];
        const start = match.index ?? 0;
        if (!labels.has(label)) {
          continue;
        }
        if (start > cursor) {
          replacements.push({ type: "text", value: node.value.slice(cursor, start) });
        }
        replacements.push({
          type: "link",
          url: `${citationLinkPrefix}${label}`,
          children: [{ type: "text", value: match[0] }],
        });
        cursor = start + match[0].length;
      }

      if (cursor === 0) {
        return;
      }
      if (cursor < node.value.length) {
        replacements.push({ type: "text", value: node.value.slice(cursor) });
      }
      parent.children.splice(index, 1, ...replacements);
    });
  };
}
