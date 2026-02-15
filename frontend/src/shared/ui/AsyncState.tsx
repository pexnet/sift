import { Alert, CircularProgress, Stack, Typography } from "@mui/material";

type AsyncStateProps = {
  isLoading: boolean;
  isError: boolean;
  empty: boolean;
  loadingLabel?: string;
  errorLabel: string;
  emptyLabel: string;
};

export function AsyncState({
  isLoading,
  isError,
  empty,
  loadingLabel = "Loading...",
  errorLabel,
  emptyLabel,
}: AsyncStateProps) {
  if (isLoading) {
    return (
      <Stack direction="row" spacing={1} alignItems="center">
        <CircularProgress size={18} />
        <Typography variant="body2" color="text.secondary">
          {loadingLabel}
        </Typography>
      </Stack>
    );
  }

  if (isError) {
    return <Alert severity="error">{errorLabel}</Alert>;
  }

  if (empty) {
    return (
      <Typography variant="body2" color="text.secondary">
        {emptyLabel}
      </Typography>
    );
  }

  return null;
}
