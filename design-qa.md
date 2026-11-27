# Fuentes design QA

Final result: passed

The selected 1586 × 992 concept and the 1280 × 800 browser captures were reviewed
at the same desktop aspect ratio, with the Actividad drawer open. The concept
shows an in-progress batch. Live checks covered a queued file, its batch
completion, and a selected document with saved fragments. Counts, filenames,
and the visibility of the batch card follow live data.

| Check | Result |
| --- | --- |
| Typography | The existing Geist and Source Serif families preserve the heading, label, and numeric hierarchy. Long filenames wrap in the drawer. |
| Layout | The sidebar, KPI strip, upload zone, table, and right drawer follow the reference. The table scrolls with live rows. At 390 px, the drawer becomes a sheet. |
| Color | Light and dark use the workspace tokens. An initial comparison found low contrast on unfilled progress tracks and the selected row. Secondary tracks and the accent row state now distinguish them. |
| Assets | The sidebar reuses the original brand mark and the workspace icon library. |
| Copy and behavior | Spanish labels distinguish indexing from chat availability. A live PDF moved from queued to indexed in review, showed its fragment count, and was deduplicated on a second upload. |

The live smoke test did not approve publication or replace a document.
