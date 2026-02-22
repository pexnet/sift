import { describe, expect, it } from "vitest";

import { toNavigationHierarchy } from "./model";

describe("toNavigationHierarchy", () => {
  it("maps systems, folders, feeds, and streams into sectioned hierarchy", () => {
    const hierarchy = toNavigationHierarchy({
      systems: [{ key: "all", title: "All articles", unread_count: 10 }],
      folders: [
        {
          id: "1714bf8e-f573-4288-b053-29592b2125fe",
          name: "Github",
          unread_count: 7,
          feeds: [{ id: "6ed3d7cf-8cf6-40f8-bce4-56a49fb95146", title: "CyberChef", unread_count: 6 }],
        },
        {
          id: null,
          name: "Unused",
          unread_count: 2,
          feeds: [{ id: "f04eb25e-c9dc-445d-8c37-41f7868cd8ab", title: "Unfiled feed", unread_count: 2 }],
        },
      ],
      streams: [
        {
          id: "0f50472d-91d5-4f9a-8820-9f72a55f7f53",
          name: "darktrace",
          folder_id: "1714bf8e-f573-4288-b053-29592b2125fe",
          unread_count: 48,
        },
      ],
    });

    expect(hierarchy.sections.map((section) => section.id)).toEqual(["systems", "monitoring", "folders"]);
    expect(hierarchy.systems[0]?.scope_id).toBe("all");
    expect(hierarchy.sections[1]?.title).toBe("Monitoring feeds");
    expect(hierarchy.folders[0]?.scope_type).toBe("folder");
    expect(hierarchy.folders[1]?.name).toBe("Unfiled");
    expect(hierarchy.folders[1]?.is_unfiled).toBe(true);
    expect(hierarchy.feeds[0]?.scope_type).toBe("feed");
    expect(hierarchy.streams[0]?.scope_type).toBe("stream");
    expect(hierarchy.streams[0]?.folder_id).toBe("1714bf8e-f573-4288-b053-29592b2125fe");
    expect(hierarchy.monitoring_folders[0]?.name).toBe("Github");
    expect(hierarchy.monitoring_folders[0]?.streams).toHaveLength(1);
  });
});
