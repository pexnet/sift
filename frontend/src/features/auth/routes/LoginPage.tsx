import { Alert, Button, Stack, TextField } from "@mui/material";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import type { FormEvent } from "react";

import { AuthCard } from "../components/AuthCard";
import { useLoginMutation } from "../api/authHooks";
import { validateEmail, validatePassword } from "../lib/validation";
import { loadPersistedWorkspaceSearch } from "../../../entities/article/model";

export function LoginPage() {
  const navigate = useNavigate();
  const loginMutation = useLoginMutation();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const emailError = validateEmail(email);
    const passwordError = validatePassword(password);
    if (emailError || passwordError) {
      setValidationError(emailError ?? passwordError);
      return;
    }

    setValidationError(null);
    loginMutation.mutate(
      { email, password },
      {
        onSuccess: () => {
          void navigate({ to: "/app", search: loadPersistedWorkspaceSearch() });
        },
      }
    );
  };

  return (
    <AuthCard title="Login" subtitle="Sign in with your local account.">
      <Stack component="form" spacing={2} onSubmit={onSubmit} noValidate>
        {validationError ? <Alert severity="error">{validationError}</Alert> : null}
        {loginMutation.error ? <Alert severity="error">{loginMutation.error.message}</Alert> : null}
        <TextField
          label="Email"
          name="email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <TextField
          label="Password"
          name="password"
          type="password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <Button type="submit" variant="contained" disabled={loginMutation.isPending}>
          {loginMutation.isPending ? "Signing in..." : "Login"}
        </Button>
      </Stack>
    </AuthCard>
  );
}
