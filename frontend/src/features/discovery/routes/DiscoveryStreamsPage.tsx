import { SettingsLayout } from "../../settings/components/SettingsLayout";

import { DiscoveryWorkbench } from "../components/DiscoveryWorkbench";

export function DiscoveryStreamsPage() {
  return (
    <SettingsLayout
      activeSection="discovery"
      title="Discover feeds"
      headingId="discovery-streams-heading"
      maxWidth={1260}
      description="Manage discovery streams, generate recommendations, and decide which feeds to add."
    >
      <DiscoveryWorkbench mode="settings" />
    </SettingsLayout>
  );
}
