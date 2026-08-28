const GITHUB_API_URL =
  "https://api.github.com/repos/jordychen0512-byte/douyin-live-notify/actions/workflows/check-live.yml/dispatches";

async function dispatchWorkflow(token) {
  return fetch(GITHUB_API_URL, {
    method: "POST",
    headers: {
      Accept: "application/vnd.github+json",
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "User-Agent": "douyin-live-notify-scheduler",
      "X-GitHub-Api-Version": "2026-03-10",
    },
    body: JSON.stringify({ ref: "main" }),
  });
}

async function triggerMonitor(env) {
  if (!env.GITHUB_TOKEN) {
    throw new Error("GITHUB_TOKEN secret is not configured");
  }

  let response;

  for (let attempt = 1; attempt <= 2; attempt += 1) {
    try {
      response = await dispatchWorkflow(env.GITHUB_TOKEN);
    } catch (error) {
      if (attempt === 2) {
        throw error;
      }
      continue;
    }

    if (response.status === 204) {
      console.log("GitHub workflow dispatched successfully");
      return;
    }

    const responseBody = await response.text();

    if (response.status < 500 || attempt === 2) {
      throw new Error(
        `GitHub dispatch failed (${response.status}): ${responseBody.slice(0, 500)}`,
      );
    }
  }
}

export default {
  async scheduled(_controller, env, ctx) {
    ctx.waitUntil(triggerMonitor(env));
  },
};
