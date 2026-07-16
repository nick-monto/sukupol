/** API helper error-path tests — non-ok response throws typed Error. */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "../src/api";

beforeEach(() => {
	vi.restoreAllMocks();
});

describe("api() error path", () => {
	it("returns data on 200", async () => {
		const mockData = { run_id: "abc" };
		vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
			new Response(JSON.stringify(mockData), { status: 200 }),
		);

		const result = await api<{ run_id: string }>("http://base", "/test");
		expect(result.run_id).toBe("abc");
	});

	it("throws Error with detail for 4xx", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
			new Response(JSON.stringify({ detail: "Not found" }), {
				status: 404,
				statusText: "Not Found",
			}),
		);

		await expect(api("http://base", "/test")).rejects.toThrow("Not found");
	});

	it("throws generic message for 5xx (no detail leaked)", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
			new Response(JSON.stringify({ detail: "Internal explosion" }), {
				status: 500,
				statusText: "Internal Server Error",
			}),
		);

		// The API helper should NOT surface detail on 5xx — only generic
		await expect(api("http://base", "/test")).rejects.toThrow(
			"Request failed with 500",
		);
	});

	it("falls back to generic message when 4xx response has no detail", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValueOnce(
			new Response("not json", { status: 400, statusText: "Bad Request" }),
		);

		await expect(api("http://base", "/test")).rejects.toThrow(
			"Request failed with 400",
		);
	});
});
