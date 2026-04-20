function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isSqliteLocked(body) {
  return /database is locked/i.test(body || '');
}

function isRetryable(resp, body) {
  return resp.status() >= 500 || isSqliteLocked(body);
}

async function postWithSqliteRetry(request, url, options, attempts = 3) {
  let lastResp = null;
  let lastBody = '';

  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    const resp = await request.post(url, options);
    if (resp.ok()) {
      return { resp, body: '' };
    }

    const body = await resp.text();
    lastResp = resp;
    lastBody = body;
    if (!isRetryable(resp, body) || attempt === attempts) {
      return { resp, body };
    }

    await sleep(150 * attempt);
  }

  return { resp: lastResp, body: lastBody };
}

module.exports = {
  postWithSqliteRetry,
};
