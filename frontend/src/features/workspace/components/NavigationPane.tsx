import {
  Button,
  FormControl,
  InputLabel,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography,
} from "@mui/material";

import type { NavigationNode } from "../../../entities/navigation/model";
import { AsyncState } from "../../../shared/ui/AsyncState";

type NavigationPaneProps = {
  density: "compact" | "comfortable";
  navItems: NavigationNode[];
  selectedScopeType: string;
  selectedScopeKey: string;
  isLoading: boolean;
  isError: boolean;
  onSelectItem: (item: NavigationNode) => void;
  onToggleTheme: () => void;
  themeMode: "light" | "dark";
  onDensityChange: (value: "compact" | "comfortable") => void;
};

export function NavigationPane({
  density,
  navItems,
  selectedScopeType,
  selectedScopeKey,
  isLoading,
  isError,
  onSelectItem,
  onToggleTheme,
  themeMode,
  onDensityChange,
}: NavigationPaneProps) {
  return (
    <Paper className="react-pane" component="section" elevation={0}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="h6">Navigation</Typography>
        <Stack direction="row" spacing={1}>
          <Button size="small" variant="outlined" onClick={onToggleTheme}>
            {themeMode === "dark" ? "Light" : "Dark"}
          </Button>
          <FormControl size="small" sx={{ minWidth: 130 }}>
            <InputLabel id="density-select">Density</InputLabel>
            <Select
              labelId="density-select"
              label="Density"
              value={density}
              onChange={(event) => onDensityChange(event.target.value)}
            >
              <MenuItem value="compact">Compact</MenuItem>
              <MenuItem value="comfortable">Comfortable</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Stack>

      <AsyncState
        isLoading={isLoading}
        isError={isError}
        empty={navItems.length === 0}
        loadingLabel="Loading navigation..."
        errorLabel="Failed to load navigation."
        emptyLabel="No navigation items."
      />

      {!isLoading && !isError ? (
        <List dense={density === "compact"}>
          {navItems.map((item) => {
            const itemKey = `${item.scope_type}:${item.scope_id}`;
            const selected = selectedScopeType === item.scope_type && selectedScopeKey === item.scope_id;
            const primaryLabel =
              item.scope_type === "system"
                ? item.title
                : item.scope_type === "folder"
                  ? item.name
                  : item.name;

            return (
              <ListItem disablePadding key={itemKey}>
                <ListItemButton selected={selected} onClick={() => onSelectItem(item)}>
                  <ListItemText
                    primary={primaryLabel}
                    secondary={item.scope_type}
                    slotProps={{
                      secondary: {
                        sx: {
                          textTransform: "capitalize",
                        },
                      },
                    }}
                  />
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      ) : null}
    </Paper>
  );
}
