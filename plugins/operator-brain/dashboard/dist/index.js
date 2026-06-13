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
    return h("div", { className: "ob-page" },
      h("header", { className: "ob-header" },
        h("div", null, h("h1", null, "Operator Brain"), h("p", null, "The autonomous engineering world, live.")),
        h(Button, { onClick: load, size: "sm" }, "Refresh"),
        h(Badge, null, data.operator.paused ? "Paused" : "Running")),
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
