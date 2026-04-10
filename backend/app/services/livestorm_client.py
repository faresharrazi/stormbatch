from __future__ import annotations

from typing import Any, Optional, Union

import httpx


class LivestormAPIError(Exception):
    pass


class LivestormClient:
    BASE_URL = "https://api.livestorm.co"

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("Livestorm API key is required")
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                # Livestorm private API tokens are sent directly. OAuth tokens are
                # the ones that require a Bearer prefix.
                "Authorization": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30,
        )

    async def __aenter__(self) -> "LivestormClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._client.aclose()

    async def create_bulk_job(self, session_id: str, tasks: list[dict]) -> dict[str, str]:
        payload = {
            "data": {
                "type": "jobs",
                "attributes": {
                    "tasks": tasks,
                },
            }
        }
        response = await self._client.post(f"/v1/sessions/{session_id}/people/bulk", json=payload)
        data = self._handle_response(response, "Livestorm API request failed")

        job_id = (
            data.get("data", {}).get("id")
            or data.get("id")
            or data.get("job_id")
        )
        if not job_id:
            raise LivestormAPIError("Livestorm API did not return a job ID")

        status = (
            data.get("data", {}).get("attributes", {}).get("status")
            or data.get("status")
            or "pending"
        )

        return {"job_id": str(job_id), "status": str(status)}

    async def register_person(self, session_id: str, fields: list[dict]) -> dict[str, Any]:
        attributes = {
            field["id"]: field.get("value", "")
            for field in fields
            if field.get("id") and field.get("value")
        }
        payload = {
            "data": {
                "type": "people",
                "attributes": attributes,
            }
        }
        response = await self._client.post(
            f"/v1/sessions/{session_id}/people",
            json=payload,
            headers={
                "Accept": "application/vnd.api+json",
                "Content-Type": "application/vnd.api+json",
            },
        )
        data = self._handle_response(response, "Livestorm single registration failed")
        return {
            "status": "succeeded",
            "raw": data,
        }

    async def get_job_status(self, session_id: str, job_id: str) -> dict[str, Any]:
        response = await self._client.get(f"/v1/jobs/{job_id}")
        job_data = self._handle_response(response, "Unable to fetch Livestorm job status")

        status = (
            job_data.get("data", {}).get("attributes", {}).get("status")
            or job_data.get("status")
            or "pending"
        )
        response = {
            "session_id": session_id,
            "job_id": job_id,
            "status": status,
            "tasks": [],
            "raw": job_data,
        }

        if str(status).lower() in {"ended", "failed", "completed"}:
            tasks_response = await self._client.get(f"/v1/jobs/{job_id}/tasks")
            if tasks_response.status_code < 400:
                tasks_data = tasks_response.json()
                response["tasks"] = tasks_data.get("data", tasks_data)

        return response

    async def list_session_people(
        self,
        session_id: str,
        email: Optional[str] = None,
        page_size: int = 50,
    ) -> list[dict[str, Any]]:
        page_number = 0
        people = []

        while True:
            params: dict[str, Union[str, int]] = {
                "page[number]": page_number,
                "page[size]": page_size,
            }
            if email:
                params["filter[email]"] = email

            response = await self._client.get(
                f"/v1/sessions/{session_id}/people",
                params=params,
                headers={"Accept": "application/vnd.api+json"},
            )
            data = self._handle_response(response, "Unable to fetch session registrants")
            page_people = data.get("data", [])
            people.extend(page_people)

            if not page_people:
                break

            meta = data.get("meta", {})
            pagination = meta.get("pagination", meta.get("page", meta))
            next_page = (
                pagination.get("next_page")
                or pagination.get("nextPage")
                or pagination.get("next")
            )
            total_pages = (
                pagination.get("total_pages")
                or pagination.get("totalPages")
                or pagination.get("page_count")
                or pagination.get("pageCount")
                or pagination.get("last")
            )
            current_page = (
                pagination.get("current_page")
                or pagination.get("currentPage")
                or pagination.get("number")
                or page_number
            )

            if next_page is None and total_pages:
                break
            if total_pages and int(current_page) + 1 >= int(total_pages):
                break
            if not total_pages and len(page_people) < page_size:
                break

            page_number = int(next_page) if next_page is not None else page_number + 1

        return people

    def _handle_response(self, response: httpx.Response, fallback_message: str) -> dict[str, Any]:
        if response.status_code >= 400:
            raise self._build_error(response, fallback_message)
        return response.json()

    def _build_error(self, response: Optional[httpx.Response], fallback_message: str) -> LivestormAPIError:
        if response is None:
            return LivestormAPIError(fallback_message)

        detail = fallback_message
        try:
            payload = response.json()
            message = payload.get("message") or payload.get("error") or payload.get("errors")
            if isinstance(message, list):
                message = ", ".join(
                    item.get("detail") or item.get("title") or str(item)
                    for item in message
                )
            if message:
                detail = f"{fallback_message}: {message}"
        except Exception:
            pass
        return LivestormAPIError(detail)
