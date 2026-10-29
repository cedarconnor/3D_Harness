# Voxel and block-grid direction

Declare voxel size in metres, grid origin and occupied-cell rules. Work in integer
grid coordinates and convert once to scene units. A voxel look is a choice about
occupancy and stepped silhouette, not merely a low polygon count or flat shading.

Block silhouettes at the chosen cell size, check small features, then assign a
limited palette. Decide whether smooth surfaces or transparent blocks are allowed
exceptions in the project. Subdivision and unplanned bevels can erase the chosen
grid language.

Repeated cubes may remain instances while editing. For an export surface, remove
hidden faces between occupied cells where appropriate. Joining objects or merging
coincident vertices alone does not remove internal cube faces. Inspect evaluated
topology, face count, normals and any atlas coordinates after conversion.

Review neighboring chunks at the same grid origin and cell size. Check boundary
gaps, duplicate faces, silhouette steps and palette consistency from the final
camera. Test export/re-import scale and occupancy on an owned copy. A visibly
blocky render does not prove a welded, manifold or fabrication-ready mesh.
