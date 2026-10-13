const STORAGE_KEY = "todos";

let todos = loadTodos();

function loadTodos() {
try {
const raw = localStorage.getItem(STORAGE_KEY);
if (!raw) return [];
const data = JSON.parse(raw);
return Array.isArray(data) ? data : [];
} catch (e) {
return [];
}
}

function saveTodos() {
localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
}

function render() {
const list = document.getElementById("todo-list");
list.innerHTML = "";

todos.forEach(function (todo, index) {
const li = document.createElement("li");
if (todo.done) {
li.classList.add("done");
}

const checkbox = document.createElement("input");
checkbox.type = "checkbox";
checkbox.checked = todo.done;
checkbox.addEventListener("change", function () {
todos[index].done = checkbox.checked;
saveTodos();
render();
});

const span = document.createElement("span");
span.className = "todo-text";
span.textContent = todo.text;

const deleteBtn = document.createElement("button");
deleteBtn.className = "delete";
deleteBtn.textContent = "×";
deleteBtn.addEventListener("click", function () {
todos.splice(index, 1);
saveTodos();
render();
});

li.appendChild(checkbox);
li.appendChild(span);
li.appendChild(deleteBtn);
list.appendChild(li);
});

const remaining = todos.filter(function (t) { return !t.done; }).length;
document.getElementById("count").textContent = "残り " + remaining + " 件";
}

function addTodo() {
const input = document.getElementById("new-todo");
const text = input.value.trim();
if (text === "") return;
todos.push({ text: text, done: false });
input.value = "";
saveTodos();
render();
}

document.getElementById("add-btn").addEventListener("click", addTodo);

document.getElementById("new-todo").addEventListener("keydown", function (e) {
if (e.key === "Enter") {
addTodo();
}
});

render();
