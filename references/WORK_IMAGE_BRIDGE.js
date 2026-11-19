// HISTORICAL ONLY — R4H.1 MUST NOT use this image-content bridge for
// stage chat delivery. Use stage_attachments with individual PNG text links.
// Retained strictly for past-implementation audit; do not execute.
// Execute inside functions.exec, after replacing paths with CURRENT absolute PNG
// paths from figure_previews. Never run this as a Node CLI or print image data.
// tools.view_image validates/retrieves the existing local image. image forwards
// an actual image output item. Submission is not proof of client painting.
const paths = []; // Populate with 1..3 actual validated paths; no model fitting.
if (paths.length < 1 || paths.length > 3) throw new Error('Supply 1..3 existing PNG paths');
for (const path of paths) {
  const result = await tools.view_image({path});
  image(result.image_url);
}
text({interface_submission: 'SUBMITTED', human_visible: 'UNVERIFIED'});
