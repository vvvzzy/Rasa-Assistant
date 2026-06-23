const chat = document.getElementById('chat');
const input = document.getElementById('msg');
const sendBtn = document.getElementById('sendBtn');
const chatTypeSelect = document.getElementById('chatType');
const quickBtns = document.querySelectorAll('.quick');
const bubbleLayer = document.getElementById('bubbleLayer');
const particleLayer = document.getElementById('particleLayer');

let senderId = localStorage.getItem('order_sender_id');
if (!senderId) {
  senderId = `web_${Math.random().toString(36).slice(2, 10)}`;
  localStorage.setItem('order_sender_id', senderId);
}

const MENU = {
  '主食面食': [
    ['牛肉面', 18, '🍜'], ['番茄鸡蛋面', 15, '🍜'], ['酸辣粉', 14, '🥣'],
    ['杂酱面', 16, '🍜'], ['油泼面', 17, '🍜'], ['馄饨面', 16, '🥣'], ['肥肠面', 22, '🍜']
  ],
  '中式盖饭': [
    ['鸡腿饭', 22, '🍗'], ['宫保鸡丁饭', 24, '🍛'], ['鱼香肉丝饭', 23, '🍛'],
    ['青椒肉丝饭', 21, '🍛'], ['红烧牛肉饭', 28, '🍛'], ['土豆丝盖饭', 16, '🍚'], ['梅菜扣肉饭', 26, '🍚']
  ],
  '西式简餐': [
    ['汉堡', 18, '🍔'], ['奥尔良烤翅', 20, '🍗'], ['意式肉酱面', 25, '🍝'],
    ['炸鸡块', 16, '🍗'], ['牛肉披萨', 39, '🍕'], ['热狗', 12, '🌭']
  ],
  '饮品': [
    ['珍珠奶茶', 12, '🧋'], ['可乐', 5, '🥤'], ['柠檬水', 8, '🍋'],
    ['橙汁', 9, '🍊'], ['冰红茶', 6, '🥤'], ['拿铁咖啡', 16, '☕']
  ],
  '小吃': [
    ['薯条', 10, '🍟'], ['鸡米花', 13, '🍗'], ['炸年糕', 11, '🍢'], ['香酥地瓜条', 12, '🍠']
  ]
};

const FOOD_IMAGE = Object.fromEntries(
  Object.values(MENU).flat().map(([name, price, emoji]) => [name, emoji])
);

function createCubeBurst(x, y, amount = 30) {
  const layer = particleLayer || document.body;

  for (let i = 0; i < amount; i++) {
    const cube = document.createElement('span');
    cube.className = 'cube-particle';

    const size = Math.random() * 8 + 6;
    const rotate = Math.random() * 360;
    const angle = (Math.PI * 2 / amount) * i + Math.random() * 0.45;
    const distance = Math.random() * 85 + 35;
    const dx = Math.cos(angle) * distance;
    const dy = Math.sin(angle) * distance;

    cube.style.setProperty('--size', `${size}px`);
    cube.style.setProperty('--rotate', `${rotate}deg`);
    cube.style.setProperty('--dx', `${dx}px`);
    cube.style.setProperty('--dy', `${dy}px`);
    cube.style.left = `${x - size / 2}px`;
    cube.style.top = `${y - size / 2}px`;

    layer.appendChild(cube);
    setTimeout(() => cube.remove(), 1700);
  }
}

function shatterElement(el, x, y) {
  el.classList.add('bubble-pop');
  createCubeBurst(x, y, 32);
  setTimeout(() => el.remove(), 240);
}

function spawnFloatingBubble() {
  if (!bubbleLayer) return;
  const bubble = document.createElement('button');
  bubble.type = 'button';
  bubble.className = 'float-bubble';
  const size = 18 + Math.random() * 42;
  bubble.style.width = `${size}px`;
  bubble.style.height = `${size}px`;
  bubble.style.left = `${Math.random() * 100}%`;
  bubble.style.setProperty('--drift', `${Math.random() * 90 - 45}px`);
  bubble.style.setProperty('--duration', `${8 + Math.random() * 8}s`);
  bubble.style.setProperty('--delay', `${Math.random() * 1.5}s`);
  bubble.addEventListener('click', (e) => {
    e.stopPropagation();
    shatterElement(bubble, e.clientX, e.clientY);
  });
  bubbleLayer.appendChild(bubble);
  setTimeout(() => bubble.remove(), 17000);
}

setInterval(spawnFloatingBubble, 650);
for (let i = 0; i < 14; i++) setTimeout(spawnFloatingBubble, i * 120);

document.addEventListener('click', (e) => {
  const target = e.target.closest('button, .message, .menu-category-card, .dish-card, .food-chip, .avatar, select, input');
  if (target) createCubeBurst(e.clientX, e.clientY, 24);
});

function getFoodEmoji(name) {
  if (FOOD_IMAGE[name]) return FOOD_IMAGE[name];
  const found = Object.keys(FOOD_IMAGE).find(food => name.includes(food) || food.includes(name));
  return found ? FOOD_IMAGE[found] : '🍽️';
}

function formatTextWithFoodImages(text) {
  const frag = document.createDocumentFragment();
  const lines = String(text || '').split('\n');

  lines.forEach((line, index) => {
    const lineWrap = document.createElement('div');
    lineWrap.className = 'rich-line';
    lineWrap.textContent = line;

    Object.keys(FOOD_IMAGE)
      .sort((a, b) => b.length - a.length)
      .forEach(food => {
        if (line.includes(food)) {
          const img = document.createElement('span');
          img.className = 'food-chip';
          img.title = food;
          img.textContent = FOOD_IMAGE[food];
          lineWrap.appendChild(img);
        }
      });

    frag.appendChild(lineWrap);
    if (index !== lines.length - 1) frag.appendChild(document.createTextNode('\n'));
  });

  return frag;
}

function shouldRenderMenu(userText, botText) {
  const t = `${userText || ''} ${botText || ''}`;
  return /菜单|菜品|有什么|推荐|今日菜单|餐品分类/.test(t);
}

function renderMenuBrowser() {
  const box = document.createElement('div');
  box.className = 'menu-browser';

  const title = document.createElement('div');
  title.className = 'menu-browser-title';
  title.innerHTML = '<strong>菜单分类</strong><span>点击分类查看实物图与价格</span>';
  box.appendChild(title);

  const categoryGrid = document.createElement('div');
  categoryGrid.className = 'menu-category-grid';

  const detail = document.createElement('div');
  detail.className = 'menu-detail';

  Object.entries(MENU).forEach(([category, items], idx) => {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'menu-category-card';
    card.innerHTML = `
      <span class="category-icon">${items[0][2]}</span>
      <span class="category-name">${category}</span>
      <small>${items.length} 款</small>
    `;
    card.addEventListener('click', (e) => {
      createCubeBurst(e.clientX, e.clientY, 28);
      categoryGrid.querySelectorAll('.menu-category-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      renderCategoryDetail(detail, category, items);
    });
    categoryGrid.appendChild(card);
    if (idx === 0) setTimeout(() => card.click(), 0);
  });

  box.appendChild(categoryGrid);
  box.appendChild(detail);
  return box;
}

function renderCategoryDetail(container, category, items) {
  container.innerHTML = '';
  const head = document.createElement('div');
  head.className = 'menu-detail-head';
  head.textContent = category;
  container.appendChild(head);

  const grid = document.createElement('div');
  grid.className = 'dish-grid';

  items.forEach(([name, price, emoji]) => {
    const dish = document.createElement('button');
    dish.type = 'button';
    dish.className = 'dish-card';
    dish.innerHTML = `
      <span class="dish-img">${emoji}</span>
      <span class="dish-info"><strong>${name}</strong><small>标准份 ¥${price}</small></span>
    `;
    dish.addEventListener('click', (e) => {
      createCubeBurst(e.clientX, e.clientY, 22);
      input.value = `我要一份${name}`;
      input.focus();
    });
    grid.appendChild(dish);
  });

  container.appendChild(grid);
}

function appendMessage(role, text, options = {}) {
  const wrapper = document.createElement('div');
  wrapper.className = `message-row ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? '用户' : '助手';

  const bubble = document.createElement('div');
  bubble.className = `message ${role}`;

  if (role === 'bot') {
    bubble.appendChild(formatTextWithFoodImages(text || '（无文本回复）'));
  } else {
    bubble.innerText = text || '（无文本回复）';
  }

  if (role === 'user') {
    wrapper.appendChild(bubble);
    wrapper.appendChild(avatar);
  } else {
    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
  }

  chat.appendChild(wrapper);

  if (role === 'bot' && shouldRenderMenu(options.userText, text)) {
    const menuRow = document.createElement('div');
    menuRow.className = 'message-row bot menu-row';
    const menuAvatar = document.createElement('div');
    menuAvatar.className = 'avatar';
    menuAvatar.textContent = '助手';
    const menuBubble = document.createElement('div');
    menuBubble.className = 'message bot menu-message';
    menuBubble.appendChild(renderMenuBrowser());
    menuRow.appendChild(menuAvatar);
    menuRow.appendChild(menuBubble);
    chat.appendChild(menuRow);
  }

  chat.scrollTop = chat.scrollHeight;
}

function appendTyping() {
  const row = document.createElement('div');
  row.className = 'message-row bot typing-row';
  row.innerHTML = '<div class="avatar">助手</div><div class="message bot typing"><i></i><i></i><i></i></div>';
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
  return row;
}

async function sendMsg(customText) {
  const text = (customText || input.value).trim();
  if (!text) return;

  appendMessage('user', text);
  input.value = '';
  input.focus();
  sendBtn.disabled = true;

  const typing = appendTyping();

  try {
    const res = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: text,
        senderId: senderId,
        chatType: chatTypeSelect ? chatTypeSelect.value : 'rasa'
      })
    });

    const data = await res.json();
    typing.remove();

    if (!res.ok) {
      appendMessage('bot', data.reply || `请求失败：HTTP ${res.status}`, { userText: text });
      return;
    }

    appendMessage('bot', data.reply || '后端没有返回文本。', { userText: text });
  } catch (error) {
    typing.remove();
    appendMessage('bot', `请求失败：${error.message}`, { userText: text });
  } finally {
    sendBtn.disabled = false;
  }
}

window.addEventListener('load', () => {
  appendMessage(
    'bot',
    '欢迎来到星厨点餐助手 ✨\n你可以说：查看菜单、我要两份牛肉面、牛肉面多少钱、查看购物车。'
  );
});

sendBtn.addEventListener('click', () => sendMsg());

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMsg();
  }
});

quickBtns.forEach((btn) => {
  btn.addEventListener('click', () => sendMsg(btn.dataset.text));
});
