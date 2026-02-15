import { CircularProgress, Paper, Stack, Typography } from "@mui/material";

import { useCurrentUser } from "../api/authHooks";

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <Stack
      direction="row"
      sx={{
        borderBottom: "1px solid",
        borderColor: "divider",
        py: 1,
      }}
      justifyContent="space-between"
      spacing={2}
    >
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="body1">{value}</Typography>
    </Stack>
  );
}

export function AccountPage() {
  const currentUserQuery = useCurrentUser();

  return (
    <Paper component="section" className="panel" sx={{ maxWidth: 640, mx: "auto" }}>
      <Typography variant="h4" component="h1" sx={{ mb: 1 }}>
        Account
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Profile and identity summary.
      </Typography>

      {currentUserQuery.isLoading ? <CircularProgress size={20} /> : null}
      {currentUserQuery.data ? (
        <Stack>
          <InfoRow label="Email" value={currentUserQuery.data.email} />
          <InfoRow label="Display Name" value={currentUserQuery.data.display_name || "(not set)"} />
          <InfoRow label="Admin" value={currentUserQuery.data.is_admin ? "yes" : "no"} />
        </Stack>
      ) : null}
    </Paper>
  );
}
