# Mock Customer Document Faces

Place mock document/front-ID images here for VNPT eKYC face compare.

Use these files as `ekyc_document_ref` in `POST /api/shield/challenge`.

Expected meaning:

- `ekyc_document_ref`: front document image or document portrait source.
- `ekyc_image_ref`: live selfie/camera image.

The public VNPT contract names the field `img_front`, so our safest assumption is a front document/passport/ID image that contains the customer portrait. If a cropped portrait is accepted by the real endpoint, we can also keep cropped face assets here, but production testing should start with the full front document image.
