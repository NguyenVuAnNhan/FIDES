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
        self._image_hash_cache: dict[str, str] = {}

    @property
    def enabled(self) -> bool:
        return self.ekyc_enabled or self.smartvoice_enabled or self.smartbot_enabled

    @property
    def mode(self) -> str:
        return f"ekyc:{self.ekyc_mode},smartvoice:{self.smartvoice_mode},smartbot:{self.smartbot_mode}"

    @property
    def ekyc_enabled(self) -> bool:
        return self._product_enabled(self._resolved_ekyc_mode(), "ekyc")

    @property
    def smartvoice_enabled(self) -> bool:
        return self._product_enabled(self._resolved_smartvoice_mode(), "smartvoice")

    @property
    def smartbot_enabled(self) -> bool:
        if not self.settings.vnpt_smartbot_bot_id:
            return False
        return self._product_enabled(self._resolved_smartbot_mode(), "smartbot")

    @property
    def ekyc_mode(self) -> str:
        return "real" if self.ekyc_enabled else "mock"

    @property
    def smartvoice_mode(self) -> str:
        return "real" if self.smartvoice_enabled else "mock"

    @property
    def smartbot_mode(self) -> str:
        return "real" if self.smartbot_enabled else "mock"

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

    def _resolved_smartbot_mode(self) -> str:
        explicit = self.settings.vnpt_smartbot_mode
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
        if product == "smartbot":
            return {
                "access_token": self.settings.vnpt_smartbot_access_token or self.settings.vnpt_access_token,
                "token_id": self.settings.vnpt_smartbot_token_id or self.settings.vnpt_token_id,
                "token_key": self.settings.vnpt_smartbot_token_key or self.settings.vnpt_token_key,
            }
        raise ValueError(f"Unsupported VNPT product: {product}")

    def add_file(
        self,
        file_path: Path,
        title: str = "ekyc",
        description: str = "ekyc",
    ) -> dict[str, Any]:
        return self._post_multipart_file(
            "/file-service/v1/addFile",
            file_path,
            base_url=self.settings.vnpt_base_url,
            provider_mode=self.ekyc_mode,
            product="ekyc",
            extra_fields={"title": title, "description": description},
            timeout=self.settings.vnpt_ekyc_request_timeout_seconds,
        )

    def face_liveness(self, image_ref: str, client_session: str) -> dict[str, Any]:
        image_hash, upload_error = self._resolve_image_hash(image_ref, title="selfie")
        if upload_error:
            return upload_error
        payload: dict[str, Any] = {
            "img": image_hash,
            "client_session": client_session,
            "token": self._ekyc_body_token(),
        }
        return self._post_json("/ai/v1/face/liveness", payload, provider_mode=self.ekyc_mode, product="ekyc")

    def face_mask(self, image_ref: str, client_session: str) -> dict[str, Any]:
        image_hash, upload_error = self._resolve_image_hash(image_ref, title="selfie")
        if upload_error:
            return upload_error
        payload: dict[str, Any] = {
            "img": image_hash,
            "client_session": client_session,
            "token": self._ekyc_body_token(),
        }
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

        document_hash, document_error = self._resolve_image_hash(document_ref, title="document")
        if document_error:
            return document_error
        face_hash, face_error = self._resolve_image_hash(face_ref, title="selfie")
        if face_error:
            return face_error
        payload: dict[str, Any] = {
            "img_front": document_hash,
            "img_face": face_hash,
            "client_session": client_session,
            "token": self._ekyc_body_token(),
        }
        return self._post_json(
            "/ai/v1/face/compare",
            payload,
            provider_mode=self.ekyc_mode,
            product="ekyc",
        )

    def smartvoice_stt(self, audio_ref: str, client_session: str) -> dict[str, Any]:
        audio_path = self._resolve_ref(audio_ref)
        if not audio_path.is_file():
            return self._error_response(
                "Local audio file not found",
                {
                    "audio_ref": audio_ref,
                    "resolved_path": str(audio_path),
                },
                provider_mode=self.smartvoice_mode,
            )

        extra_fields: dict[str, str] = {
            "clientSession": client_session,
            "model": "offline",
            "maxAlternatives": "1",
            "audioChannelCount": "1",
        }
        if self.settings.vnpt_stt_cap_punct_recovery.lower() in {"true", "1", "yes"}:
            extra_fields["enableAutomaticPunctuation"] = "true"
        suffix = audio_path.suffix.lower()
        if suffix in {".mp3", ".mpeg"}:
            extra_fields["customConfiguration"] = json.dumps(
                {
                    "invert_text": "1",
                    "cap_punct_recovery": self.settings.vnpt_stt_cap_punct_recovery,
                    "convert_format": "mp3",
                }
            )
        elif suffix == ".webm":
            extra_fields["customConfiguration"] = json.dumps(
                {
                    "invert_text": "1",
                    "cap_punct_recovery": self.settings.vnpt_stt_cap_punct_recovery,
                    "convert_format": "mp3",
                }
            )

        return self._post_multipart_file(
            "/stt-service/v1/grpc/standard",
            audio_path,
            self.settings.vnpt_base_url,
            provider_mode=self.smartvoice_mode,
            product="smartvoice",
            extra_fields=extra_fields,
            file_field_name="audioFile",
            file_content_type=self._audio_content_type(audio_path),
            timeout=self.settings.vnpt_request_timeout_seconds,
        )

    def smartbot_conversation(
        self,
        text: str,
        session_id: str,
        sender_id: str | None = None,
    ) -> dict[str, Any]:
        if not text.strip():
            return self._error_response(
                "Smartbot conversation text is empty",
                {"session_id": session_id},
                provider_mode=self.smartbot_mode,
            )

        payload: dict[str, Any] = {
            "bot_id": self.settings.vnpt_smartbot_bot_id,
            "sender_id": sender_id or self.settings.vnpt_smartbot_sender_id,
            "text": text,
            "input_channel": self.settings.vnpt_smartbot_input_channel,
            "session_id": session_id,
            "metadata": {"button_variables": []},
        }
        return self._post_json(
            "/v1/conversation",
            payload,
            provider_mode=self.smartbot_mode,
            product="smartbot",
            base_url=self.settings.vnpt_smartbot_base_url,
            timeout=self.settings.vnpt_smartbot_request_timeout_seconds,
        )

    def _post_json(
        self,
        path: str,
        payload: dict[str, Any],
        provider_mode: str | None = None,
        product: str = "ekyc",
        base_url: str | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = self._auth_headers("application/json", product=product)
        if product == "ekyc":
            selected_timeout = timeout or self.settings.vnpt_ekyc_request_timeout_seconds
        elif product == "smartbot":
            selected_timeout = timeout or self.settings.vnpt_smartbot_request_timeout_seconds
        else:
            selected_timeout = timeout or self.settings.vnpt_request_timeout_seconds
        return self._request(
            path,
            body,
            headers,
            provider_mode=provider_mode,
            base_url=base_url,
            timeout=selected_timeout,
        )

    def _post_multipart_file(
        self,
        path: str,
        file_path: Path,
        base_url: str,
        provider_mode: str | None = None,
        product: str = "smartvoice",
        extra_fields: dict[str, str] | None = None,
        timeout: float | None = None,
        file_field_name: str = "file",
        file_content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        boundary = f"----fides-{uuid.uuid4().hex}"
        parts: list[bytes] = []
        for field_name, field_value in (extra_fields or {}).items():
            parts.extend(
                [
                    f"--{boundary}\r\n".encode("utf-8"),
                    f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'.encode("utf-8"),
                    field_value.encode("utf-8"),
                    b"\r\n",
                ]
            )
        parts.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{file_field_name}"; '
                    f'filename="{file_path.name}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {file_content_type}\r\n\r\n".encode("utf-8"),
                file_path.read_bytes(),
                b"\r\n",
                f"--{boundary}--\r\n".encode("utf-8"),
            ]
        )
        headers = self._auth_headers(f"multipart/form-data; boundary={boundary}", product=product)
        return self._request(
            path,
            b"".join(parts),
            headers,
            base_url=base_url,
            provider_mode=provider_mode,
            timeout=timeout or self.settings.vnpt_request_timeout_seconds,
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

    def _ekyc_body_token(self) -> str:
        explicit = str(self.settings.vnpt_ekyc_token or "").strip()
        if explicit:
            return explicit
        return str(self.settings.vnpt_ekyc_token_id or "").strip()

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

    def _looks_like_vnpt_hash(self, value: str) -> bool:
        normalized = value.strip()
        return bool(normalized) and "/" in normalized and (
            normalized.startswith("idg") or "IDG" in normalized
        )

    def _resolve_image_hash(
        self,
        image_ref: str,
        title: str = "face",
    ) -> tuple[str | None, dict[str, Any] | None]:
        if self._looks_like_vnpt_hash(image_ref):
            return image_ref, None

        path = self._resolve_ref(image_ref)
        if not path.is_file():
            return image_ref, None

        cache_key = str(path.resolve())
        cached_hash = self._image_hash_cache.get(cache_key)
        if cached_hash:
            return cached_hash, None

        upload = self.add_file(path, title=title, description=title)
        hash_value = self._nested_value(upload, ["object", "hash"])
        if not hash_value:
            return None, self._error_response(
                "VNPT addFile did not return object.hash",
                {
                    "image_ref": image_ref,
                    "resolved_path": str(path),
                    "upload_response": upload,
                },
                provider_mode=self.ekyc_mode,
            )

        hash_str = str(hash_value)
        self._image_hash_cache[cache_key] = hash_str
        return hash_str, None

    def _audio_content_type(self, path: Path) -> str:
        mapping = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".mpeg": "audio/mpeg",
            ".webm": "audio/webm",
            ".ogg": "audio/ogg",
            ".m4a": "audio/mp4",
            ".aac": "audio/aac",
        }
        return mapping.get(path.suffix.lower(), self.settings.vnpt_stt_content_type)

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
