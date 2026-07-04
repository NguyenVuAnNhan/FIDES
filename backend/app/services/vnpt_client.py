import base64
import json
from pathlib import Path
from typing import Any
from urllib import error, request

from backend.app.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class VnptClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return (
            self.settings.vnpt_provider_mode.lower() == "real"
            and bool(self.settings.vnpt_access_token)
            and bool(self.settings.vnpt_token_id)
            and bool(self.settings.vnpt_token_key)
        )

    @property
    def mode(self) -> str:
        return "real" if self.enabled else "mock"

    def face_liveness(self, image_ref: str, client_session: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "img": self._image_payload(image_ref),
            "client_session": client_session,
        }
        if self.settings.vnpt_ekyc_token:
            payload["token"] = self.settings.vnpt_ekyc_token
        return self._post_json("/ai/v1/face/liveness", payload)

    def face_mask(self, image_ref: str, client_session: str) -> dict[str, Any]:
        return self._post_json(
            "/ai/v1/face/mask",
            {
                "img": self._image_payload(image_ref),
                "client_session": client_session,
            },
        )

    def face_compare(
        self,
        document_ref: str | None,
        face_ref: str,
        client_session: str,
    ) -> dict[str, Any]:
        if not document_ref:
            return {
                "message": "Skipped face compare because no document image was provided",
                "object": {
                    "result": "MATCH",
                    "msg": "SKIPPED_NO_DOCUMENT",
                    "prob": 1.0,
                },
                "provider_mode": self.mode,
            }

        payload: dict[str, Any] = {
            "img_front": self._image_payload(document_ref),
            "img_face": self._image_payload(face_ref),
            "client_session": client_session,
        }
        if self.settings.vnpt_ekyc_token:
            payload["token"] = self.settings.vnpt_ekyc_token
        return self._post_json("/ai/v1/face/compare", payload)

    def smartvoice_stt(self, audio_ref: str) -> dict[str, Any]:
        audio_path = self._resolve_ref(audio_ref)
        if not audio_path.exists():
            return self._error_response(
                "Local audio file not found",
                {
                    "audio_ref": audio_ref,
                    "resolved_path": str(audio_path),
                },
            )

        headers = {
            "Enable-Lm": self.settings.vnpt_stt_enable_lm,
            "Sample-Rate": str(self.settings.vnpt_stt_sample_rate),
            "bit-per-rate": str(self.settings.vnpt_stt_bit_per_rate),
            "domain": self.settings.vnpt_stt_domain,
            "save-log": self.settings.vnpt_stt_save_log,
            "cap_punct_recovery": self.settings.vnpt_stt_cap_punct_recovery,
        }
        return self._post_binary(
            "/stt-service/v3/standard",
            audio_path.read_bytes(),
            self.settings.vnpt_stt_content_type,
            headers,
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = self._auth_headers("application/json")
        return self._request(path, body, headers)

    def _post_binary(
        self,
        path: str,
        body: bytes,
        content_type: str,
        extra_headers: dict[str, str],
    ) -> dict[str, Any]:
        headers = {**self._auth_headers(content_type), **extra_headers}
        return self._request(path, body, headers)

    def _request(self, path: str, body: bytes, headers: dict[str, str]) -> dict[str, Any]:
        url = f"{self.settings.vnpt_base_url.rstrip('/')}/{path.lstrip('/')}"
        req = request.Request(url=url, data=body, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=20) as response:
                response_body = response.read()
                parsed = self._parse_json(response_body)
                if isinstance(parsed, dict):
                    parsed.setdefault("provider_mode", self.mode)
                    parsed.setdefault("http_status", response.status)
                    return parsed
                return {
                    "message": "VNPT returned a non-object JSON payload",
                    "object": parsed,
                    "provider_mode": self.mode,
                    "http_status": response.status,
                }
        except error.HTTPError as exc:
            return self._error_response(
                "VNPT request failed",
                {
                    "http_status": exc.code,
                    "endpoint_path": path,
                    "body": self._decode_error_body(exc),
                },
            )
        except error.URLError as exc:
            return self._error_response(
                "VNPT request could not be completed",
                {
                    "endpoint_path": path,
                    "reason": str(exc.reason),
                },
            )
        except TimeoutError:
            return self._error_response(
                "VNPT request timed out",
                {
                    "endpoint_path": path,
                },
            )

    def _auth_headers(self, content_type: str) -> dict[str, str]:
        headers = {
            "Content-Type": content_type,
            "Authorization": f"Bearer {self.settings.vnpt_access_token}",
            "Token-id": str(self.settings.vnpt_token_id),
            "Token-key": str(self.settings.vnpt_token_key),
        }
        if self.settings.vnpt_mac_address:
            headers["mac-address"] = self.settings.vnpt_mac_address
        return headers

    def _image_payload(self, image_ref: str) -> str:
        path = self._resolve_ref(image_ref)
        if path.exists():
            return base64.b64encode(path.read_bytes()).decode("ascii")
        return image_ref

    def _resolve_ref(self, ref: str) -> Path:
        path = Path(ref)
        if path.is_absolute():
            return path
        return PROJECT_ROOT / path

    def _error_response(self, message: str, details: dict[str, Any]) -> dict[str, Any]:
        return {
            "message": message,
            "object": {},
            "status": "error",
            "provider_mode": self.mode,
            "error": details,
        }

    def _parse_json(self, body: bytes) -> Any:
        if not body:
            return {}
        try:
            return json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {
                "message": "VNPT returned a non-JSON response",
                "raw_response_preview": body[:500].decode("utf-8", errors="replace"),
            }

    def _decode_error_body(self, exc: error.HTTPError) -> Any:
        body = exc.read()
        parsed = self._parse_json(body)
        return parsed
