(function () {
  "use strict";

  const STORAGE_KEY = "todo-items";

  const input = document.getElementById("new-todo");
  const addBtn = document.getElementById("add-btn");
  const list = document.getElementById("todo-list");
  const countEl = document.getElementById("count");

  let todos = load();

  function load() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const data = JSON.parse(raw);
      if (!Array.isArray(data)) return [];
      return data
        .filter(function (t) { return t && typeof t.text === "string"; })
        .map(function (t) { return { id: t.id, text: t.text, done: !!t.done }; });
    } catch (e) {
      return [];
    }
  }

  function save() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
  }

  function updateCount() {
    const remaining = todos.filter(function (t) { return !t.done; }).length;
    countEl.textContent = "残り " + remaining + " 件";
  }

  function createItem(todo) {
    const li = document.createElement("li");
    if (todo.done) li.className = "done";
    li.dataset.id = todo.id;

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = todo.done;
    checkbox.addEventListener("change", function () {
      todo.done = checkbox.checked;
      li.classList.toggle("done", todo.done);
      save();
      updateCount();
    });

    const span = document.createElement("span");
    span.className = "text";
    span.textContent = todo.text;

    const delBtn = document.createElement("button");
    delBtn.className = "delete";
    delBtn.textContent = "削除";
    delBtn.addEventListener("click", function () {
      todos = todos.filter(function (t) { return t.id !== todo.id; });
      li.remove();
      save();
      updateCount();
    });

    li.appendChild(checkbox);
    li.appendChild(span);
    li.appendChild(delBtn);
    return li;
  }

  function render() {
    list.innerHTML = "";
    todos.forEach(function (todo) {
      list.appendChild(createItem(todo));
    });
    updateCount();
  }

  function addTodo() {
    const text = input.value.trim();
    if (!text) return;
    const todo = {
      id: Date.now() + "-" + Math.random().toString(36).slice(2),
      text: text,
      done: false
    };
    todos.push(todo);
    list.appendChild(createItem(todo));
    input.value = "";
    input.focus();
    save();
    updateCount();
  }

  addBtn.addEventListener("click", addTodo);

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") {
      addTodo();
    }
  });

  render();
})();
