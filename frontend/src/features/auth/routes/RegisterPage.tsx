import { Alert, Button, Stack, TextField } from "@mui/material";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import type { FormEvent } from "react";

import { useRegisterMutation } from "../api/authHooks";
import { AuthCard } from "../components/AuthCard";
import { validateEmail, validatePassword } from "../lib/validation";
import { loadPersistedWorkspaceSearch } from "../../../entities/article/model";

export function RegisterPage() {
  const navigate = useNavigate();
  const registerMutation = useRegisterMutation();

  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
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
    registerMutation.mutate(
      {
        email,
        password,
        display_name: displayName,
      },
      {
        onSuccess: () => {
          void navigate({ to: "/app", search: loadPersistedWorkspaceSearch() });
        },
      }
    );
  };

  return (
    <AuthCard title="Register" subtitle="Create a local account.">
      <Stack component="form" spacing={2} onSubmit={onSubmit} noValidate>
        {validationError ? <Alert severity="error">{validationError}</Alert> : null}
        {registerMutation.error ? <Alert severity="error">{registerMutation.error.message}</Alert> : null}
        <TextField
          label="Email"
          name="email"
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
        <TextField
          label="Display Name"
          name="display_name"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
        />
        <TextField
          label="Password"
          name="password"
          type="password"
          required
          value={password}
          onChange={(event) => setPassword(event.target.value)}
        />
        <Button type="submit" variant="contained" disabled={registerMutation.isPending}>
          {registerMutation.isPending ? "Creating..." : "Create Account"}
        </Button>
      </Stack>
    </AuthCard>
  );
}
