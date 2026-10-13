(function () {
  "use strict";

  var STORAGE_KEY = "todo-app-items";

  var input = document.getElementById("new-todo");
  var addBtn = document.getElementById("add-btn");
  var list = document.getElementById("todo-list");
  var countEl = document.getElementById("count");

  var todos = load();

  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      var data = JSON.parse(raw);
      return Array.isArray(data) ? data : [];
    } catch (e) {
      return [];
    }
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
  }

  function render() {
    list.innerHTML = "";
    todos.forEach(function (todo, index) {
      var li = document.createElement("li");
      if (todo.done) li.className = "done";

      var checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = todo.done;
      checkbox.addEventListener("change", function () {
        todos[index].done = checkbox.checked;
        save();
        render();
      });
      li.appendChild(checkbox);

      var span = document.createElement("span");
      span.className = "text";
      span.textContent = todo.text;
      li.appendChild(span);

      var delBtn = document.createElement("button");
      delBtn.className = "delete";
      delBtn.textContent = "削除";
      delBtn.addEventListener("click", function () {
        todos.splice(index, 1);
        save();
        render();
      });
      li.appendChild(delBtn);

      list.appendChild(li);
    });
    updateCount();
  }

  function updateCount() {
    var remaining = todos.filter(function (t) { return !t.done; }).length;
    countEl.textContent = "残り " + remaining + " 件";
  }

  function addTodo() {
    var text = input.value.trim();
    if (!text) return;
    todos.push({ text: text, done: false });
    input.value = "";
    save();
    render();
    input.focus();
  }

  addBtn.addEventListener("click", addTodo);

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") addTodo();
  });

  render();
})();
