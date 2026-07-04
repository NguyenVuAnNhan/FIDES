import base64
import json
import uuid
from pathlib import Path
from typing import Any
from urllib import parse
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

    def smartvoice_voice_verify(
        self,
        reference_audio_ref: str | None,
        challenge_audio_ref: str,
        client_session: str,
    ) -> dict[str, Any]:
        if not reference_audio_ref:
            return {
                "message": "Skipped voice verification because no customer voice reference was provided",
                "object": {
                    "ok": True,
                    "result": {
                        "similarity": 1.0,
                        "score": 1.0,
                    },
                },
                "provider_mode": self.mode,
                "skipped": True,
            }

        reference_upload = self._voice_upload(reference_audio_ref)
        challenge_upload = self._voice_upload(challenge_audio_ref)
        reference_url = self._nested_value(reference_upload, ["object", "result"])
        challenge_url = self._nested_value(challenge_upload, ["object", "result"])
        if not reference_url or not challenge_url:
            return self._error_response(
                "Voice verification upload failed",
                {
                    "reference_upload": reference_upload,
                    "challenge_upload": challenge_upload,
                },
            )

        reference_encode = self._voice_encode(str(reference_url), registered=1, client_session=client_session)
        challenge_encode = self._voice_encode(str(challenge_url), registered=0, client_session=client_session)
        reference_audio_id = self._nested_value(reference_encode, ["object", "result"])
        challenge_audio_id = self._nested_value(challenge_encode, ["object", "result"])
        if not reference_audio_id or not challenge_audio_id:
            return self._error_response(
                "Voice verification encoding failed",
                {
                    "reference_encode": reference_encode,
                    "challenge_encode": challenge_encode,
                },
            )

        verification = self._voice_verify_ids(str(reference_audio_id), str(challenge_audio_id))
        verification.setdefault(
            "provider_trace",
            {
                "reference_upload": reference_upload,
                "challenge_upload": challenge_upload,
                "reference_encode": reference_encode,
                "challenge_encode": challenge_encode,
            },
        )
        return verification

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

    def _voice_upload(self, audio_ref: str) -> dict[str, Any]:
        audio_path = self._resolve_ref(audio_ref)
        if not audio_path.exists():
            return self._error_response(
                "Local voice sample file not found",
                {
                    "audio_ref": audio_ref,
                    "resolved_path": str(audio_path),
                },
            )
        return self._post_multipart_file("/v1/voice-id/audio/upload", audio_path, self.settings.vnpt_voice_base_url)

    def _voice_encode(self, audio_url: str, registered: int, client_session: str) -> dict[str, Any]:
        return self._post_json_to_base(
            self.settings.vnpt_voice_base_url,
            "/v1/voice-id/audio/encode",
            {
                "audio_url": audio_url,
                "registered": registered,
                "client_session": client_session,
                "data": {
                    "email": self.settings.vnpt_voice_verify_email,
                    "name": self.settings.vnpt_voice_verify_name,
                },
            },
        )

    def _voice_verify_ids(self, audio_id1: str, audio_id2: str) -> dict[str, Any]:
        query = parse.urlencode({"audio_id1": audio_id1, "audio_id2": audio_id2})
        return self._get_json(f"/voiceid/api/v1/audio/verify?{query}", self.settings.vnpt_voice_base_url)

    def _post_json_to_base(self, base_url: str, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = self._auth_headers("application/json")
        return self._request(path, body, headers, base_url=base_url)

    def _post_multipart_file(self, path: str, file_path: Path, base_url: str) -> dict[str, Any]:
        boundary = f"----fides-{uuid.uuid4().hex}"
        body = b"".join(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    'Content-Disposition: form-data; name="file"; '
                    f'filename="{file_path.name}"\r\n'
                ).encode("utf-8"),
                b"Content-Type: application/octet-stream\r\n\r\n",
                file_path.read_bytes(),
                b"\r\n",
                f"--{boundary}--\r\n".encode("utf-8"),
            ]
        )
        headers = self._auth_headers(f"multipart/form-data; boundary={boundary}")
        return self._request(path, body, headers, base_url=base_url)

    def _get_json(self, path: str, base_url: str) -> dict[str, Any]:
        headers = self._auth_headers("application/json")
        return self._request(path, None, headers, method="GET", base_url=base_url)

    def _request(
        self,
        path: str,
        body: bytes | None,
        headers: dict[str, str],
        method: str = "POST",
        base_url: str | None = None,
    ) -> dict[str, Any]:
        selected_base_url = base_url or self.settings.vnpt_base_url
        url = f"{selected_base_url.rstrip('/')}/{path.lstrip('/')}"
        req = request.Request(url=url, data=body, headers=headers, method=method)
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

    def _nested_value(self, payload: dict[str, Any], keys: list[str]) -> Any:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current
