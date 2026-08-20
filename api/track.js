const GH_API = "https://api.github.com";

function csvEscape(value) {
  const text = String(value || "");
  return `"${text.replace(/"/g, '""')}"`;
}

function toBase64Utf8(text) {
  return Buffer.from(text, "utf8").toString("base64");
}

function fromBase64Utf8(text) {
  return Buffer.from(text || "", "base64").toString("utf8");
}

async function getCsvFile(owner, repo, path, token) {
  const safePath = encodeURIComponent(path).replace(/%2F/g, "/");
  const url = `${GH_API}/repos/${owner}/${repo}/contents/${safePath}`;

  const res = await fetch(url, {
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28"
    }
  });

  if (res.status === 404) {
    return {
      sha: null,
      content: "clicked_at,campaign,link_type,tech_id,category,target_url,user_agent,source_app\n"
    };
  }

  if (!res.ok) {
    throw new Error(`GitHub read failed: ${res.status}`);
  }

  const data = await res.json();

  return {
    sha: data.sha,
    content: fromBase64Utf8(data.content)
  };
}

async function saveCsvFile(owner, repo, path, token, content, sha) {
  const safePath = encodeURIComponent(path).replace(/%2F/g, "/");
  const url = `${GH_API}/repos/${owner}/${repo}/contents/${safePath}`;

  const body = {
    message: "Append newsletter click log",
    content: toBase64Utf8(content),
    branch: "main"
  };

  if (sha) {
    body.sha = sha;
  }

  const res = await fetch(url, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      Accept: "application/vnd.github+json",
      "Content-Type": "application/json",
      "X-GitHub-Api-Version": "2022-11-28"
    },
    body: JSON.stringify(body)
  });

  if (!res.ok) {
    throw new Error(`GitHub write failed: ${res.status}`);
  }
}

export default async function handler(req, res) {
  const target = req.query.target;

  if (!target || !String(target).startsWith("https://")) {
    return res.status(400).send("Invalid target");
  }

  try {
    const token = process.env.GITHUB_TOKEN;
    const repoFull = process.env.GITHUB_REPO;
    const logPath = process.env.CLICK_LOG_PATH || "logs/click_logs.csv";

    if (!token || !repoFull) {
      throw new Error("Missing GITHUB_TOKEN or GITHUB_REPO");
    }

    const [owner, repo] = repoFull.split("/");
    const file = await getCsvFile(owner, repo, logPath, token);

    const row = [
      new Date().toISOString(),
      req.query.campaign || "",
      req.query.link_type || "",
      req.query.tech_id || "",
      req.query.category || "",
      target,
      req.headers["user-agent"] || "",
      "pnuth-tech-tracker"
    ].map(csvEscape).join(",") + "\n";

    await saveCsvFile(owner, repo, logPath, token, file.content + row, file.sha);
  } catch (error) {
    console.error(error);
  }

  return res.redirect(302, target);
}
