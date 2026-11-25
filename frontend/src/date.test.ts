import { afterEach, describe, expect, it, vi } from "vitest";
import { hojeLocal } from "./format";

describe("B9 – data local (fuso de Brasília)", () => {
  afterEach(() => vi.useRealTimers());

  it("às 22:54 de Brasília devolve o próprio dia, não o seguinte (UTC)", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2027-03-11T01:54:00Z")); // 10/03/2027 22:54 em Brasília
    expect(hojeLocal()).toBe("2027-03-10");
  });
});
