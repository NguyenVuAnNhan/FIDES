import base64
import http.client
import json
import ssl
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from backend.app.config import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class VnptClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return self.ekyc_enabled or self.smartvoice_enabled

    @property
    def mode(self) -> str:
        return f"ekyc:{self.ekyc_mode},smartvoice:{self.smartvoice_mode}"

    @property
    def ekyc_enabled(self) -> bool:
        return self._product_enabled(self._resolved_ekyc_mode(), "ekyc")

    @property
    def smartvoice_enabled(self) -> bool:
        return self._product_enabled(self._resolved_smartvoice_mode(), "smartvoice")

    @property
    def ekyc_mode(self) -> str:
        return "real" if self.ekyc_enabled else "mock"

    @property
    def smartvoice_mode(self) -> str:
        return "real" if self.smartvoice_enabled else "mock"

    def _resolved_ekyc_mode(self) -> str:
        explicit = self.settings.vnpt_ekyc_mode
        if explicit:
            return explicit.lower()
        return self.settings.vnpt_provider_mode.lower()

    def _resolved_smartvoice_mode(self) -> str:
        explicit = self.settings.vnpt_smartvoice_mode
        if explicit:
            return explicit.lower()
        return self.settings.vnpt_provider_mode.lower()

    def _product_enabled(self, mode: str, product: str) -> bool:
        credentials = self._product_credentials(product)
        return (
            mode == "real"
            and bool(credentials["access_token"])
            and bool(credentials["token_id"])
            and bool(credentials["token_key"])
        )

    def _product_credentials(self, product: str) -> dict[str, str | None]:
        if product == "ekyc":
            return {
                "access_token": self.settings.vnpt_ekyc_access_token or self.settings.vnpt_access_token,
                "token_id": self.settings.vnpt_ekyc_token_id or self.settings.vnpt_token_id,
                "token_key": self.settings.vnpt_ekyc_token_key or self.settings.vnpt_token_key,
            }
        if product == "smartvoice":
            return {
                "access_token": self.settings.vnpt_smartvoice_access_token or self.settings.vnpt_access_token,
                "token_id": self.settings.vnpt_smartvoice_token_id or self.settings.vnpt_token_id,
                "token_key": self.settings.vnpt_smartvoice_token_key or self.settings.vnpt_token_key,
            }
        raise ValueError(f"Unsupported VNPT product: {product}")

    def face_liveness(self, image_ref: str, client_session: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "img": self._image_payload(image_ref),
            "client_session": client_session,
        }
        product_token = self._ekyc_product_token()
        if product_token:
            payload["token"] = product_token
        return self._post_json("/ai/v1/face/liveness", payload, provider_mode=self.ekyc_mode, product="ekyc")

    def face_mask(self, image_ref: str, client_session: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "img": self._image_payload(image_ref),
            "client_session": client_session,
        }
        product_token = self._ekyc_product_token()
        if product_token:
            payload["token"] = product_token
        return self._post_json(
            "/ai/v1/face/mask",
            payload,
            provider_mode=self.ekyc_mode,
            product="ekyc",
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
                "provider_mode": self.ekyc_mode,
            }

        payload: dict[str, Any] = {
            "img_front": self._image_payload(document_ref),
            "img_face": self._image_payload(face_ref),
            "client_session": client_session,
        }
        product_token = self._ekyc_product_token()
        if product_token:
            payload["token"] = product_token
        return self._post_json(
            "/ai/v1/face/compare",
            payload,
            provider_mode=self.ekyc_mode,
            product="ekyc",
        )

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
            product="smartvoice",
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
                "provider_mode": self.smartvoice_mode,
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

    def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        provider_mode: str | None = None,
        product: str = "ekyc",
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = self._auth_headers("application/json", product=product)
        timeout = (
            self.settings.vnpt_ekyc_request_timeout_seconds
            if product == "ekyc"
            else self.settings.vnpt_request_timeout_seconds
        )
        return self._request(path, body, headers, provider_mode=provider_mode, timeout=timeout)

    def _post_binary(
        self,
        path: str,
        body: bytes,
        content_type: str,
        extra_headers: dict[str, str],
        product: str = "smartvoice",
    ) -> dict[str, Any]:
        headers = {**self._auth_headers(content_type, product=product), **extra_headers}
        return self._request(
            path,
            body,
            headers,
            provider_mode=self.smartvoice_mode,
            timeout=self.settings.vnpt_request_timeout_seconds,
        )

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
        return self._post_multipart_file(
            "/v1/voice-id/audio/upload",
            audio_path,
            self.settings.vnpt_voice_base_url,
            provider_mode=self.smartvoice_mode,
            product="smartvoice",
        )

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
            provider_mode=self.smartvoice_mode,
            product="smartvoice",
        )

    def _voice_verify_ids(self, audio_id1: str, audio_id2: str) -> dict[str, Any]:
        query = f"audio_id1={audio_id1}&audio_id2={audio_id2}"
        return self._get_json(
            f"/voiceid/api/v1/audio/verify?{query}",
            self.settings.vnpt_voice_base_url,
            provider_mode=self.smartvoice_mode,
            product="smartvoice",
        )

    def _post_json_to_base(
        self,
        base_url: str,
        path: str,
        payload: dict[str, Any],
        provider_mode: str | None = None,
        product: str = "smartvoice",
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        headers = self._auth_headers("application/json", product=product)
        return self._request(
            path,
            body,
            headers,
            base_url=base_url,
            provider_mode=provider_mode,
            timeout=self.settings.vnpt_request_timeout_seconds,
        )

    def _post_multipart_file(
        self,
        path: str,
        file_path: Path,
        base_url: str,
        provider_mode: str | None = None,
        product: str = "smartvoice",
    ) -> dict[str, Any]:
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
        headers = self._auth_headers(f"multipart/form-data; boundary={boundary}", product=product)
        return self._request(
            path,
            body,
            headers,
            base_url=base_url,
            provider_mode=provider_mode,
            timeout=self.settings.vnpt_request_timeout_seconds,
        )

    def _get_json(
        self,
        path: str,
        base_url: str,
        provider_mode: str | None = None,
        product: str = "smartvoice",
    ) -> dict[str, Any]:
        headers = self._auth_headers("application/json", product=product)
        return self._request(
            path,
            None,
            headers,
            method="GET",
            base_url=base_url,
            provider_mode=provider_mode,
        )

    def _request(
        self,
        path: str,
        body: bytes | None,
        headers: dict[str, str],
        method: str = "POST",
        base_url: str | None = None,
        provider_mode: str | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        selected_base_url = base_url or self.settings.vnpt_base_url
        selected_provider_mode = provider_mode or self.mode
        selected_timeout = timeout or self.settings.vnpt_request_timeout_seconds
        url = f"{selected_base_url.rstrip('/')}/{path.lstrip('/')}"
        parsed = urlparse(url)
        request_path = parsed.path or "/"
        if parsed.query:
            request_path = f"{request_path}?{parsed.query}"

        connection = http.client.HTTPSConnection(
            parsed.netloc,
            timeout=selected_timeout,
            context=ssl.create_default_context(),
        )
        try:
            connection.putrequest(method, request_path)
            for header_name, header_value in headers.items():
                connection.putheader(header_name, header_value)
            if body is not None:
                connection.putheader("Content-Length", str(len(body)))
            connection.endheaders()
            if body is not None:
                connection.send(body)

            response = connection.getresponse()
            response_body = response.read()
            parsed_json = self._parse_json(response_body)
            if isinstance(parsed_json, dict):
                parsed_json.setdefault("provider_mode", selected_provider_mode)
                parsed_json.setdefault("http_status", response.status)
                return parsed_json
            return {
                "message": "VNPT returned a non-object JSON payload",
                "object": parsed_json,
                "provider_mode": selected_provider_mode,
                "http_status": response.status,
            }
        except TimeoutError:
            return self._error_response(
                "VNPT request timed out",
                {"endpoint_path": path},
                provider_mode=selected_provider_mode,
            )
        except OSError as exc:
            return self._error_response(
                "VNPT request could not be completed",
                {"endpoint_path": path, "reason": str(exc)},
                provider_mode=selected_provider_mode,
            )
        finally:
            connection.close()

    def _ekyc_product_token(self) -> str | None:
        explicit = str(self.settings.vnpt_ekyc_token or "").strip()
        if explicit:
            return explicit
        fallback = str(self.settings.vnpt_ekyc_token_id or "").strip()
        return fallback or None

    def _auth_headers(self, content_type: str, product: str = "ekyc") -> dict[str, str]:
        credentials = self._product_credentials(product)
        access_token = str(credentials["access_token"] or "").strip()
        if access_token.lower().startswith("bearer "):
            access_token = access_token[7:].strip()
        headers = {
            "Content-Type": content_type,
            "Authorization": f"Bearer {access_token}",
            "Token-id": str(credentials["token_id"]),
            "Token-key": str(credentials["token_key"]),
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

    def _error_response(
        self,
        message: str,
        details: dict[str, Any],
        provider_mode: str | None = None,
    ) -> dict[str, Any]:
        return {
            "message": message,
            "object": {},
            "status": "error",
            "provider_mode": provider_mode or self.mode,
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

    def _nested_value(self, payload: dict[str, Any], keys: list[str]) -> Any:
        current: Any = payload
        for key in keys:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
        return current
