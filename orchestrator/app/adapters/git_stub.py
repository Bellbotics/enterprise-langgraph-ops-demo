from __future__ import annotations

from typing import Dict

def build_patch_diff(state: Dict[str, object]) -> str:
    # A demo diff that represents a config repo change (Helm values / app config).
    scenario = state.get("scenario", "unknown")
    if scenario == "hikari_pool_exhaustion":
        return """diff --git a/values.yaml b/values.yaml
index 1111111..2222222 100644
--- a/values.yaml
+++ b/values.yaml
@@ -10,6 +10,14 @@ app:
   env:
-    HIKARI_MAX_POOL_SIZE: "20"
-    HIKARI_CONNECTION_TIMEOUT_MS: "30000"
+    # Proposed: tune pool + timeouts after verifying DB saturation/locks.
+    # NOTE: approval required in staging/prod.
+    HIKARI_MAX_POOL_SIZE: "30"
+    HIKARI_CONNECTION_TIMEOUT_MS: "20000"
+    HIKARI_MAX_LIFETIME_MS: "1200000"
+    HIKARI_LEAK_DETECTION_THRESHOLD_MS: "20000"
+
+  # Proposed: reduce heavy reporting workload on request path.
+  features:
+    async_reporting: true
"""
    if scenario == "pdf_heavy_memory":
        return """diff --git a/deployments.yaml b/deployments.yaml
index 3333333..4444444 100644
--- a/deployments.yaml
+++ b/deployments.yaml
@@ -1,10 +1,26 @@
 apiDeployment:
   replicas: 3
 workerDeployment:
-  enabled: false
+  # Proposed: isolate heavy PDF processing into separate worker deployment.
+  enabled: true
+  replicas: 2
+  resources:
+    requests:
+      memory: "2Gi"
+    limits:
+      memory: "6Gi"
+
+queue:
+  # Proposed: durable work queue between API and heavy worker.
+  enabled: true
"""
    return """diff --git a/README.md b/README.md
index 5555555..6666666 100644
--- a/README.md
+++ b/README.md
@@ -1,3 +1,5 @@
+# No-op patch
+This demo scenario did not generate a specific patch.
"""
