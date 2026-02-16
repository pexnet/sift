import { Alert, Box, Button, Paper, Stack, Typography } from "@mui/material";

function SyntaxExample({ query, description }: { query: string; description: string }) {
  return (
    <Box sx={{ mb: 1.1 }}>
      <Typography variant="body2" sx={{ fontFamily: "Consolas, SFMono-Regular, Menlo, monospace" }}>
        {query}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {description}
      </Typography>
    </Box>
  );
}

export function HelpPage() {
  return (
    <Paper component="section" className="panel settings-panel" sx={{ maxWidth: 980, mx: "auto" }} aria-labelledby="help-heading">
      <Stack spacing={2.2}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          alignItems={{ xs: "flex-start", md: "center" }}
          justifyContent="space-between"
          spacing={1}
        >
          <Box>
            <Typography id="help-heading" variant="h4" component="h1">
              Help
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.6 }}>
              Monitoring feed setup and search syntax reference.
            </Typography>
          </Box>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <Button component="a" href="/account/monitoring" size="small" variant="outlined">
              Open monitoring feeds
            </Button>
            <Button component="a" href="/account" size="small" variant="outlined">
              Back to settings
            </Button>
          </Stack>
        </Stack>

        <Alert severity="info">
          Use <strong>Search query (v1)</strong> for boolean logic, and use include/exclude keyword or regex fields for additional filters.
        </Alert>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" component="h2">
            Configure a monitoring feed
          </Typography>
          <Stack spacing={1} sx={{ mt: 1 }}>
            <Typography variant="body2">1. Set a clear feed name (for example: `Threat Intel - Microsoft`).</Typography>
            <Typography variant="body2">2. Add a Search query to define the core matching logic.</Typography>
            <Typography variant="body2">3. Add include keywords for must-have terms and exclude keywords for noise terms.</Typography>
            <Typography variant="body2">4. Add include/exclude regex (one pattern per line) for structured patterns like CVE IDs.</Typography>
            <Typography variant="body2">5. Optionally set source/language constraints and classifier mode/plugin.</Typography>
            <Typography variant="body2">6. Save, then run backfill to apply your updated definition to existing articles.</Typography>
          </Stack>
        </Paper>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" component="h2" sx={{ mb: 1 }}>
            Search query syntax (v1)
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Supported operators and precedence: <strong>NOT</strong> then <strong>AND</strong> then <strong>OR</strong>.
          </Typography>
          <SyntaxExample query={`microsoft AND sentinel`} description="Both terms must match." />
          <SyntaxExample query={`microsoft OR defender`} description="Either term can match." />
          <SyntaxExample query={`microsoft AND NOT sports`} description="Exclude unwanted terms." />
          <SyntaxExample query={`(microsoft OR azure) AND sentinel`} description="Use parentheses for grouping." />
          <SyntaxExample query={`"threat intelligence"`} description="Quoted phrase match." />
          <SyntaxExample query={`malwar*`} description="Suffix wildcard (prefix match)." />
          <SyntaxExample query={`defnder~1`} description="Fuzzy term match (distance 1 or 2)." />
          <Typography variant="caption" color="text.secondary">
            Adjacent terms are treated like `AND` (for example: `microsoft sentinel`).
          </Typography>
        </Paper>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6" component="h2" sx={{ mb: 1 }}>
            Regex and exclude behavior
          </Typography>
          <Stack spacing={0.8}>
            <Typography variant="body2">- Include regex: at least one include regex pattern must match.</Typography>
            <Typography variant="body2">- Exclude regex: any exclude regex hit blocks the match.</Typography>
            <Typography variant="body2">- Exclude keywords: any keyword hit blocks the match.</Typography>
          </Stack>
        </Paper>
      </Stack>
    </Paper>
  );
}
