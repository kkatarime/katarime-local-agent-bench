(function () {
  "use strict";

  var STORAGE_KEY = "todo-a…s-v1";

  var input = document.getElementById("new-todo");
  var addBtn = document.getElementById("add-btn");
  var list = document.getElementById("todo-list");
  var countEl = document.getElementById("count");

  // todos: [{ id, text, done }]
  var todos = load();

  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      var data = JSON.parse(raw);
      if (!Array.isArray(data)) return [];
      return data.filter(function (t) {
        return t && typeof t.text === "string";
      }).map(function (t) {
        return { id: t.id, text: t.text, done: !!t.done };
      });
    } catch (e) {
      return [];
    }
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
  }

  function render() {
    list.innerHTML = "";
    todos.forEach(function (todo) {
      var li = document.createElement("li");
      if (todo.done) li.className = "done";

      var checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = todo.done;
      checkbox.addEventListener("change", function () {
        todo.done = checkbox.checked;
        save();
        render();
      });

      var span = document.createElement("span");
      span.className = "text";
      span.textContent = todo.text;

      var delBtn = document.createElement("button");
      delBtn.className = "delete";
      delBtn.textContent = "削除";
      delBtn.addEventListener("click", function () {
        todos = todos.filter(function (t) { return t.id !== todo.id; });
        save();
        render();
      });

      li.appendChild(checkbox);
      li.appendChild(span);
      li.appendChild(delBtn);
      list.appendChild(li);
    });

    var remaining = todos.filter(function (t) { return !t.done; }).length;
    countEl.textContent = "残り " + remaining + " 件";
  }

  function addTodo() {
    var text = input.value.trim();
    if (!text) return;
    todos.push({ id: Date.now() + "-" + Math.random(), text: text, done: false });
    input.value = "";
    input.focus();
    save();
    render();
  }

  addBtn.addEventListener("click", addTodo);

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") addTodo();
  });

  render();
})();
