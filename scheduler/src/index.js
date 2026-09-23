// Shared existing Worker: preserve Douyin checks and add YouTube every five minutes.
export const REPOSITORIES = ["douyin-live-notify", "youtube-live-notify"];

export async function triggerMonitor(env, repo, fetcher = fetch) {
  if (!env.GITHUB_TOKEN) throw new Error("GITHUB_TOKEN secret is not configured");
  const url = `https://api.github.com/repos/jordychen0512-byte/${repo}/actions/workflows/check-live.yml/dispatches`;
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    let response;
    try {
      response = await fetcher(url, {
        method: "POST",
        headers: {
          Accept: "application/vnd.github+json",
          Authorization: `Bearer ${env.GITHUB_TOKEN}`,
          "Content-Type": "application/json",
          "User-Agent": "douyin-live-notify-scheduler",
          "X-GitHub-Api-Version": "2022-11-28",
        },
        body: JSON.stringify({ ref: "main" }),
        signal: AbortSignal.timeout(20000),
      });
    } catch (error) {
      if (attempt === 2) throw new Error(`${repo}: dispatch network failure`, { cause: error });
      continue;
    }
    if (response.status === 204) {
      console.log(`${repo}: GitHub workflow dispatched successfully`);
      return;
    }
    await response.text();
    if (response.status < 500 || attempt === 2) {
      throw new Error(`${repo}: GitHub dispatch failed (${response.status})`);
    }
  }
}

export async function triggerAll(env, fetcher = fetch) {
  const results = await Promise.allSettled(REPOSITORIES.map(repo => triggerMonitor(env, repo, fetcher)));
  const failures = results.filter(result => result.status === "rejected");
  for (const failure of failures) console.error(failure.reason.message);
  if (failures.length) throw new AggregateError(failures.map(f => f.reason), "Monitor dispatch failed");
}

export default {
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil(triggerAll(env));
  },
};
