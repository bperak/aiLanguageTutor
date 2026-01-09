FROM mcr.microsoft.com/playwright:v1.51.1-jammy

# Reason: The base Playwright image includes browsers, but does not guarantee the Node module
# is available for `import 'playwright'` in our MCP runner script.
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

WORKDIR /work

# Minimal install of the Playwright Node module so `frontend/scripts/mcp_runner.mjs` can use
# `import('playwright')` when scenarios include browser navigation.
RUN npm init -y >/dev/null 2>&1 \
  && npm install --silent --no-progress playwright@1.51.1

ENTRYPOINT ["sleep", "infinity"]


