(function () {
  "use strict";
  const SDK = window.__HERMES_PLUGIN_SDK__;
  if (!SDK) return;
  const h = SDK.React.createElement;
  const { useEffect, useState } = SDK.hooks;
  const { Card, CardContent, Badge, Button } = SDK.components;

  function section(title, items, render) {
    return h("section", { className: "ob-section" },
      h("h2", null, title),
      h("div", { className: "ob-grid" }, (items || []).map(render)));
  }

  function OperatorBrain() {
    const [data, setData] = useState(null);
    const [error, setError] = useState("");
    function load() {
      SDK.fetchJSON("/api/plugins/operator-brain/snapshot")
        .then(setData).catch(function (err) { setError(String(err)); });
    }
    useEffect(function () {
      load();
      const timer = setInterval(load, 10000);
      return function () { clearInterval(timer); };
    }, []);
    if (error) return h("div", { className: "ob-error" }, error);
    if (!data) return h("div", null, "Loading Operator Brain...");
    const proving = data.proving_ground || {};
    const cleanup = data.workspace_cleanup || {};
    const lifecycle = data.branch_lifecycle || {};
    const machineOps = data.machine_ops || {};
    const council = data.operator_council || {};
    const researchPolicy = data.online_research_policy || {};
    const coderPerformance = data.coder_performance || ((data.operator_intelligence || {}).coder_performance) || {};
    const failureRecipes = data.failure_recipes || ((data.operator_intelligence || {}).failure_recipes) || {};
    const skillRatings = ((data.agent_skill_ratings || {}).ratings) || {};
    const ratingItems = Object.keys(skillRatings).map(function (key) {
      const item = skillRatings[key] || {};
      return { key: key, score: item.score, title: item.title, evidence: item.evidence };
    });
    return h("div", { className: "ob-page" },
      h("header", { className: "ob-header" },
        h("div", null, h("h1", null, "Operator Brain"), h("p", null, "The autonomous engineering world, live.")),
        h(Button, { onClick: load, size: "sm" }, "Refresh"),
        h(Badge, null, data.operator.paused ? "Paused" : "Running")),
      section("Overwatch Proving Ground", [proving], function (item) {
        return h(Card, { key: "overwatch-proving-ground" }, h(CardContent, null,
          h("strong", null, "Phase " + String(item.current_phase || "?") + " / " + String(item.pending_total || 0) + " tasks pending"),
          h("div", null, String(item.consecutive_successes || 0) + " consecutive successes; target " + String(item.target_attempts || 10)),
          h("div", null, "PR: " + String((item.latest_pull_request || {}).status || "none") +
            " / merge: " + String((item.latest_merge || {}).status || "none") +
            " / validation: " + String((item.latest_validation || {}).status || "unknown")),
          item.failure_improvement_contract ? h("div", null,
            "Improvement contracts: " + String(item.failure_improvement_contract.pending_count || 0) + " pending") : null,
          h(Badge, null, item.model_blocked ? "Blocked: model offline" : (item.ready_for_more_repos ? "Ready for more repos" : "Benchmark running"))));
      }),
      section("Operator Council", council.roles || [], function (item, index) {
        return h(Card, { key: item.role || index }, h(CardContent, null,
          h("strong", null, item.role || "Council role"),
          h("div", null, item.focus || ""),
          h(Badge, null, item.vote || "unknown")));
      }),
      section("Skill Ratings", ratingItems, function (item) {
        return h(Card, { key: item.key }, h(CardContent, null,
          h("strong", null, item.key.replace(/_/g, " ")),
          h("div", null, "score: " + String(item.score || "?") + " / 10"),
          item.evidence ? h("div", null, item.evidence) : null,
          h(Badge, null, item.title || "unknown")));
      }),
      section("Coder Performance", [coderPerformance], function (item) {
        const quality = item.quality || {};
        const delivered = item.delivered_task_to_pr_minutes || {};
        const raw = item.task_to_pr_minutes || {};
        const throughput = item.delivered_throughput || item.throughput || {};
        const failures = quality.failure_counts || {};
        return h(Card, { key: "coder-performance" }, h(CardContent, null,
          h("strong", null, "Overwatch coder speed"),
          h("div", null, "delivered median task-to-PR: " + String(delivered.median || 0) + " minutes"),
          h("div", null, "raw median task-to-PR: " + String(raw.median || 0) + " minutes"),
          h("div", null, "coding pass ratio: " + String(quality.coding_round_pass_ratio || 0)),
          h("div", null, "delivery ratio: " + String(quality.delivery_success_ratio || 0)),
          h("div", null, "failures: " + JSON.stringify(failures)),
          h("div", null, "throughput: " + String(throughput.status || "unknown") +
            (throughput.files_per_hour ? " / " + String(throughput.files_per_hour) + " files/hour" : "")),
          h(Badge, null, item.workspace || "unknown")));
      }),
      section("Failure Recipes", failureRecipes.recipes || [], function (item, index) {
        return h(Card, { key: item.failure_type || index }, h(CardContent, null,
          h("strong", null, item.failure_type || "failure"),
          h("div", null, "count: " + String(item.count || 0)),
          h("div", null, item.recipe || ""),
          item.retry_policy ? h("div", null, "retry: " + item.retry_policy) : null,
          h(Badge, null, "recipe")));
      }),
      section("Online Research Policy", [researchPolicy], function (item) {
        return h(Card, { key: "online-research-policy" }, h(CardContent, null,
          h("strong", null, "Default: " + String(item.default || "unknown")),
          h("div", null, String(item.planner_rule || "")),
          h("div", null, "Allowed: " + String((item.allowed_without_human_approval || []).length) + " categories"),
          h(Badge, null, item.status || "unknown")));
      }),
      section("Workspace Cleanup", cleanup.results || lifecycle.sync_results || [], function (item, index) {
        const classification = item.classification || item;
        return h(Card, { key: item.workspace || index }, h(CardContent, null,
          h("strong", null, item.workspace || "Workspace"),
          h("div", null, "branch: " + String(item.branch || "?")),
          h("div", null, String(classification.reason || item.reason || "")),
          item.backup_branch ? h("div", null, "backup: " + item.backup_branch) : null,
          h(Badge, null, String(classification.status || item.status || "unknown"))));
      }),
      section("Branch Lifecycle", lifecycle.pruned_branches || [], function (item, index) {
        return h(Card, { key: (item.workspace || "") + (item.branch || index) }, h(CardContent, null,
          h("strong", null, item.branch || "Branch"),
          h("div", null, item.workspace || ""),
          h("div", null, "reason: " + String(item.reason || "unknown")),
          h(Badge, null, "pruned")));
      }),
      section("Machine Ops", machineOps.latest_requests || [], function (item, index) {
        return h(Card, { key: item.id || item.file || index }, h(CardContent, null,
          h("strong", null, item.action || "Machine operation"),
          h("div", null, item.reason || ""),
          h("div", null, "risk: " + String(item.risk || "unknown") +
            " / approval: " + (item.approval_required ? "human" : "auto") +
            " / exec: " + String(item.execution_status || item.dry_run_status || "not run")),
          item.expected_impact ? h("div", null, "impact: " + item.expected_impact) : null,
          item.rollback ? h("div", null, "rollback: " + item.rollback) : null,
          h(Badge, null, item.status || "unknown")));
      }),
      section("Overwatch Benchmark Attempts", proving.attempts || [], function (item, index) {
        const stages = item.stages || {};
        const stageText = ["coding", "pull_request", "merged", "deployed", "healthcheck"]
          .map(function (name) { return name + ":" + (stages[name] ? "pass" : "wait"); }).join(" / ");
        return h(Card, { key: item.timestamp || index }, h(CardContent, null,
          h("strong", null, item.summary || "Attempt"),
          h("div", null, stageText),
          item.failure_type ? h("div", null, "Failure: " + item.failure_type) : null,
          item.retry_reason ? h("div", null, "Retry reason: " + item.retry_reason) : null,
          item.improvement_contract && item.improvement_contract.required ?
            h("div", null, "Improvement required: " + String(item.improvement_contract.status || "pending")) : null,
          h(Badge, null, item.status || "incomplete")));
      }),
      section("Agents", data.agents, function (item) {
        return h(Card, { key: item.name }, h(CardContent, null,
          h("strong", null, item.name), h("div", null, item.role), h(Badge, null, item.status)));
      }),
      section("Repositories", data.workspaces, function (item) {
        return h(Card, { key: item.name }, h(CardContent, null,
          h("strong", null, item.name), h("div", null, item.type + " / " + item.risk),
          h(Badge, null, item.cycle_status)));
      }),
      section("Recent Tasks", data.tasks.slice(0, 12), function (item) {
        return h(Card, { key: item.file }, h(CardContent, null,
          h("strong", null, item.summary || item.file),
          h("div", null, (item.workspace || "") + " / " + (item.task_type || "")),
          h(Badge, null, item.status || "recorded")));
      }),
      section("Hypotheses", data.hypotheses.slice(0, 12), function (item, index) {
        return h(Card, { key: item.key || index }, h(CardContent, null,
          h("strong", null, item.summary || "Hypothesis"),
          h("div", null, item.workspace || ""),
          h(Badge, null, "score " + String(item.score || 0))));
      }),
      section("Skills", data.skills.slice(0, 12), function (item) {
        return h(Card, { key: item.path }, h(CardContent, null, h("strong", null, item.name)));
      }));
  }

  if (window.__HERMES_PLUGINS__) window.__HERMES_PLUGINS__.register("operator-brain", OperatorBrain);
})();
