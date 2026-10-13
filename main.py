import os, json, base64, mimetypes, threading
import requests, certifi
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.audio import SoundLoader
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.properties import ColorProperty, NumericProperty
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.modalview import ModalView
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import platform

# ---------------------------------------------------------------- theme
BG = (.914, .914, .922, 1)
CARD = (.965, .965, .969, 1)
SOFT = (.855, .855, .867, 1)
DARK = (.075, .075, .08, 1)
GRAY = (.54, .54, .56, 1)
WHITE = (1, 1, 1, 1)
Window.clearcolor = BG
Window.softinput_mode = "below_target"

# Положи свой шрифт в fonts/ui.ttf - он подхватится сам.
UI_FONT = "fonts/ui.ttf" if os.path.exists("fonts/ui.ttf") else "Roboto"
ICON_FONT = "icons.ttf"  # Material Icons (скачивается при сборке)
I = {"chat": 0xe0cb, "settings": 0xe8b8, "send": 0xe163, "attach": 0xe226,
     "play": 0xe037, "pause": 0xe034, "add": 0xe145, "delete": 0xe872,
     "close": 0xe5cd, "key": 0xe0da, "audio": 0xe3a1, "check": 0xe5ca}

# ---------------------------------------------------------------- models (13.10.2026)
PROVIDERS = {
    "anthropic": ("Claude", [("Fable 5.1", "claude-fable-5-1"), ("Opus 5.5", "claude-opus-5-5"),
                             ("Sonnet 5.5", "claude-sonnet-5-5"), ("Haiku 5.5", "claude-haiku-5-5")]),
    "openai": ("OpenAI", [("GPT-6 Astra", "gpt-6-astra"), ("GPT-6.1 Sol", "gpt-6.1-sol"),
                          ("GPT-6 Luna", "gpt-6-luna"), ("GPT-5.6 Sol", "gpt-5.6-sol")]),
    "google": ("Gemini", [("Gemini 3.5 Flash", "gemini-3.5-flash"),
                          ("Gemini 3.1 Flash-Lite", "gemini-3.1-flash-lite")]),
}
MAX_KEYS = 30


# ---------------------------------------------------------------- widgets
class Card(BoxLayout):
    bg = ColorProperty(CARD)
    radius = NumericProperty(dp(20))

    def __init__(self, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self._c = Color(*self.bg)
            self._r = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        self.bind(pos=self._u, size=self._u, bg=self._u, radius=self._u)

    def _u(self, *a):
        self._c.rgba = self.bg
        self._r.pos, self._r.size, self._r.radius = self.pos, self.size, [self.radius]


class Btn(ButtonBehavior, Card):
    def __init__(self, text=None, icon=None, fg=DARK, bg=SOFT, fs=14, **kw):
        kw.setdefault("padding", dp(8))
        super().__init__(bg=bg, **kw)
        self.lbl = Label(text=chr(I[icon]) if icon else text, color=fg,
                         font_name=ICON_FONT if icon else UI_FONT,
                         font_size=dp(22) if icon else dp(fs), halign="center",
                         valign="middle", shorten=True)
        self.lbl.bind(size=lambda w, v: setattr(w, "text_size", v))
        self.add_widget(self.lbl)

    def on_state(self, *a):
        self.opacity = .65 if self.state == "down" else 1

    def style(self, dark):
        self.bg = DARK if dark else SOFT
        self.lbl.color = WHITE if dark else DARK


def field(hint, password=False):
    card = Card(size_hint_y=None, height=dp(48), bg=SOFT, radius=dp(14))
    ti = TextInput(hint_text=hint, password=password, multiline=False, font_name=UI_FONT,
                   background_normal="", background_active="", background_color=(0, 0, 0, 0),
                   foreground_color=DARK, hint_text_color=GRAY, cursor_color=DARK,
                   padding=[dp(14), dp(14)])
    card.add_widget(ti)
    return card, ti


def text_label(text, color=DARK, fs=15, **kw):
    l = Label(text=text, color=color, font_name=UI_FONT, font_size=dp(fs), halign="left",
              valign="middle", **kw)
    l.bind(size=lambda w, v: setattr(w, "text_size", v))
    return l


def title(text):
    l = text_label(text.upper(), GRAY, 12, size_hint_y=None, height=dp(34))
    return l


class Player(BoxLayout):
    def __init__(self, path, dark, **kw):
        super().__init__(size_hint_y=None, height=dp(44), spacing=dp(10), **kw)
        self.path, self.snd, self.pos_s, self.ev = path, None, 0, None
        self.btn = Btn(icon="play", fg=DARK if dark else WHITE, bg=WHITE if dark else DARK,
                       size_hint=(None, None), size=(dp(42), dp(42)), radius=dp(21))
        self.btn.bind(on_release=self.toggle)
        self.add_widget(self.btn)
        self.add_widget(text_label(os.path.basename(path), WHITE if dark else DARK, 13))
        self.t = text_label("0:00", GRAY, 12, size_hint_x=None, width=dp(78))
        self.add_widget(self.t)

    def toggle(self, *a):
        if self.snd is None:
            self.snd = SoundLoader.load(self.path)
            if not self.snd:
                self.t.text = "ошибка"
                return
            self.snd.bind(on_stop=self.stopped)
        if self.snd.state == "play":
            self.pos_s = self.snd.get_pos()
            self.snd.unbind(on_stop=self.stopped)
            self.snd.stop()
            self.snd.bind(on_stop=self.stopped)
            self.halt()
        else:
            self.snd.play()
            if self.pos_s:
                self.snd.seek(self.pos_s)
            self.btn.lbl.text = chr(I["pause"])
            self.ev = Clock.schedule_interval(self.tick, .5)

    def halt(self):
        self.btn.lbl.text = chr(I["play"])
        if self.ev:
            self.ev.cancel()

    def stopped(self, *a):
        self.pos_s = 0
        self.halt()

    def tick(self, dt):
        p, l = int(self.snd.get_pos()), int(self.snd.length or 0)
        self.t.text = "%d:%02d / %d:%02d" % (p // 60, p % 60, l // 60, l % 60)


# ---------------------------------------------------------------- API
def call_api(k, model, hist):
    p, key = k["provider"], k["key"]

    def ok(r):
        try:
            j = r.json()
        except Exception:
            raise Exception(r.text[:300])
        if r.status_code != 200:
            e = j.get("error", j)
            raise Exception(e.get("message", str(e)) if isinstance(e, dict) else str(e))
        return j

    kw = dict(timeout=120, verify=certifi.where())
    if p == "anthropic":
        msgs = []
        for m in hist:
            c = []
            if m["media"] and m["media"][0].startswith("image/"):
                c.append({"type": "image", "source": {"type": "base64",
                          "media_type": m["media"][0], "data": m["media"][1]}})
            c.append({"type": "text", "text": m["text"] or "."})
            msgs.append({"role": m["role"], "content": c})
        j = ok(requests.post("https://api.anthropic.com/v1/messages",
                             headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                             json={"model": model, "max_tokens": 4096, "messages": msgs}, **kw))
        return "".join(b.get("text", "") for b in j["content"])
    if p == "openai":
        msgs = []
        for m in hist:
            c = [{"type": "text", "text": m["text"] or "."}]
            if m["media"] and m["media"][0].startswith("image/"):
                c.append({"type": "image_url", "image_url":
                          {"url": "data:%s;base64,%s" % (m["media"][0], m["media"][1])}})
            msgs.append({"role": m["role"], "content": c})
        j = ok(requests.post("https://api.openai.com/v1/chat/completions",
                             headers={"Authorization": "Bearer " + key},
                             json={"model": model, "messages": msgs}, **kw))
        return j["choices"][0]["message"]["content"]
    cs = []
    for m in hist:
        parts = [{"text": m["text"] or "."}]
        if m["media"] and m["media"][0].split("/")[0] in ("image", "audio"):
            mt = "audio/mpeg" if m["media"][0] == "audio/mp3" else m["media"][0]
            parts.append({"inline_data": {"mime_type": mt, "data": m["media"][1]}})
        cs.append({"role": "user" if m["role"] == "user" else "model", "parts": parts})
    j = ok(requests.post("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % model,
                         headers={"x-goog-api-key": key}, json={"contents": cs}, **kw))
    return "".join(x.get("text", "") for x in j["candidates"][0]["content"]["parts"])


# ---------------------------------------------------------------- store
class Store:
    def __init__(self, path):
        self.path = path
        self.d = {"keys": [], "sel": -1, "custom": {}}
        try:
            self.d.update(json.load(open(path)))
        except Exception:
            pass

    def save(self):
        json.dump(self.d, open(self.path, "w"))


def model_name(provider, mid):
    for n, i in PROVIDERS[provider][1]:
        if i == mid:
            return n
    return mid


def models_for(app, provider):
    base = list(PROVIDERS[provider][1])
    base += [(m, m) for m in app.store.d["custom"].get(provider, [])]
    return base


# ---------------------------------------------------------------- chat
class ChatView(BoxLayout):
    def __init__(self, app, **kw):
        super().__init__(orientation="vertical", spacing=dp(10), **kw)
        self.app, self.hist, self.att = app, [], None

        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.key_btn = Btn(text="", bg=SOFT)
        self.key_btn.bind(on_release=self.pick_key)
        self.model_btn = Btn(text="", bg=SOFT)
        self.model_btn.bind(on_release=self.pick_model)
        top.add_widget(self.key_btn)
        top.add_widget(self.model_btn)
        self.add_widget(top)

        self.sv = ScrollView(bar_width=0)
        self.box = GridLayout(cols=1, spacing=dp(10), size_hint_y=None)
        self.box.bind(minimum_height=self.box.setter("height"))
        self.sv.add_widget(self.box)
        self.add_widget(self.sv)

        self.chip = Btn(text="", fs=12, bg=SOFT, size_hint_y=None, height=0, opacity=0)
        self.chip.bind(on_release=self.clear_att)
        self.add_widget(self.chip)

        bar = Card(size_hint_y=None, height=dp(56), bg=CARD, padding=[dp(6), dp(6)], spacing=dp(6))
        a = Btn(icon="attach", size_hint_x=None, width=dp(44), radius=dp(16))
        a.bind(on_release=self.pick_file)
        self.inp = TextInput(hint_text="Сообщение", multiline=True, font_name=UI_FONT,
                             background_normal="", background_active="", background_color=(0, 0, 0, 0),
                             foreground_color=DARK, hint_text_color=GRAY, cursor_color=DARK,
                             padding=[dp(6), dp(12)])
        s = Btn(icon="send", fg=WHITE, bg=DARK, size_hint_x=None, width=dp(44), radius=dp(16))
        s.bind(on_release=self.send)
        for w in (a, self.inp, s):
            bar.add_widget(w)
        self.add_widget(bar)
        self.refresh()

    # chips
    def refresh(self):
        k = self.app.cur_key()
        if k:
            self.key_btn.lbl.text = "%02d  %s" % (self.app.store.d["sel"] + 1, k["name"])
            self.model_btn.lbl.text = model_name(k["provider"], self.app.cur_model(k))
        else:
            self.key_btn.lbl.text, self.model_btn.lbl.text = "NO KEY", "-"

    def pick_key(self, *a):
        v = ModalView(size_hint=(.92, None), height=dp(380), background="", background_color=(0, 0, 0, .35))
        c = Card(orientation="vertical", padding=dp(16), spacing=dp(10), bg=CARD)
        c.add_widget(title("API ключи  %d / %d" % (len(self.app.store.d["keys"]), MAX_KEYS)))
        g = GridLayout(cols=5, spacing=dp(8))
        keys = self.app.store.d["keys"]
        for i in range(MAX_KEYS):
            has = i < len(keys)
            b = Btn(text="%d" % (i + 1), radius=dp(14), bg=DARK if i == self.app.store.d["sel"] else SOFT,
                    fg=WHITE if i == self.app.store.d["sel"] else (DARK if has else GRAY))
            if has:
                b.bind(on_release=lambda w, i=i: (self.app.select_key(i), v.dismiss()))
            b.opacity = 1 if has else .45
            g.add_widget(b)
        c.add_widget(g)
        v.add_widget(c)
        v.open()

    def pick_model(self, *a):
        k = self.app.cur_key()
        if not k:
            return
        ms = models_for(self.app, k["provider"])
        v = ModalView(size_hint=(.92, None), height=dp(90 + 54 * len(ms)), background="",
                      background_color=(0, 0, 0, .35))
        c = Card(orientation="vertical", padding=dp(16), spacing=dp(8), bg=CARD)
        c.add_widget(title("Модель · " + PROVIDERS[k["provider"]][0]))
        for n, i in ms:
            cur = i == self.app.cur_model(k)
            b = Btn(text=n, bg=DARK if cur else SOFT, fg=WHITE if cur else DARK, size_hint_y=None, height=dp(46))
            b.bind(on_release=lambda w, i=i: (self.app.set_model(i), v.dismiss()))
            c.add_widget(b)
        v.add_widget(c)
        v.open()

    # attachments
    def pick_file(self, *a):
        try:
            from plyer import filechooser
            filechooser.open_file(on_selection=lambda s: Clock.schedule_once(lambda dt: self.set_att(s), 0),
                                  filters=[["Media", "*.png", "*.jpg", "*.jpeg", "*.webp", "*.mp3", "*.m4a", "*.wav"]])
        except Exception as e:
            self.add_msg("assistant", "Не удалось открыть выбор файла: %s" % e)

    def set_att(self, sel):
        if sel:
            self.att = sel[0]
            self.chip.lbl.text = "x  " + os.path.basename(self.att)
            self.chip.height, self.chip.opacity = dp(34), 1

    def clear_att(self, *a):
        self.att = None
        self.chip.height, self.chip.opacity = 0, 0

    # messages
    def add_msg(self, role, text, media=None):
        user = role == "user"
        fg = WHITE if user else DARK
        card = Card(orientation="vertical", bg=DARK if user else CARD, padding=dp(14),
                    spacing=dp(8), size_hint=(.86, None))
        card.bind(minimum_height=card.setter("height"))
        if media:
            if media[0].startswith("image/"):
                card.add_widget(Image(source=media[2], size_hint_y=None, height=dp(180), fit_mode="contain"))
            else:
                card.add_widget(Player(media[2], user))
        lbl = Label(text=text, color=fg, font_name=UI_FONT, font_size=dp(15), size_hint_y=None,
                    halign="left", valign="top")
        lbl.bind(width=lambda w, v: setattr(w, "text_size", (v, None)),
                 texture_size=lambda w, v: setattr(w, "height", v[1]))
        if text or not media:
            card.add_widget(lbl)
        row = BoxLayout(size_hint_y=None)
        row.bind(minimum_height=row.setter("height"))
        if user:
            row.add_widget(Widget(size_hint_x=.14))
            row.add_widget(card)
        else:
            row.add_widget(card)
            row.add_widget(Widget(size_hint_x=.14))
        self.box.add_widget(row)
        Clock.schedule_once(lambda dt: setattr(self.sv, "scroll_y", 0), .1)
        return lbl

    def send(self, *a):
        txt = self.inp.text.strip()
        if not (txt or self.att):
            return
        k = self.app.cur_key()
        if not k:
            self.add_msg("assistant", "Добавь API ключ: нижняя кнопка → настройки.")
            return
        media = None
        if self.att:
            try:
                mt = mimetypes.guess_type(self.att)[0] or "application/octet-stream"
                media = (mt, base64.b64encode(open(self.att, "rb").read()).decode(), self.att)
            except Exception as e:
                self.add_msg("assistant", "Файл не прочитан: %s" % e)
                return
        self.inp.text = ""
        self.clear_att()
        self.add_msg("user", txt, media)
        self.hist.append({"role": "user", "text": txt, "media": media})
        out = self.add_msg("assistant", "...")
        model, hist = self.app.cur_model(k), list(self.hist)

        def work():
            try:
                res = call_api(k, model, hist)
                self.hist.append({"role": "assistant", "text": res, "media": None})
            except Exception as e:
                res = "Ошибка: %s" % e
                self.hist.pop()
            Clock.schedule_once(lambda dt: (setattr(out, "text", res),
                                            setattr(self.sv, "scroll_y", 0)), 0)
        threading.Thread(target=work, daemon=True).start()


# ---------------------------------------------------------------- settings
class SettingsView(ScrollView):
    prov = "anthropic"

    def __init__(self, app, **kw):
        super().__init__(bar_width=0, **kw)
        self.app = app
        self.build()

    def build(self):
        self.clear_widgets()
        st = self.app.store.d
        g = GridLayout(cols=1, spacing=dp(10), size_hint_y=None, padding=[0, 0, 0, dp(20)])
        g.bind(minimum_height=g.setter("height"))

        g.add_widget(title("API ключи  %d / %d" % (len(st["keys"]), MAX_KEYS)))
        for i, k in enumerate(st["keys"]):
            r = Card(size_hint_y=None, height=dp(56), padding=[dp(14), dp(6)], spacing=dp(8),
                     bg=DARK if i == st["sel"] else CARD)
            fg = WHITE if i == st["sel"] else DARK
            r.add_widget(text_label("%02d" % (i + 1), GRAY, 13, size_hint_x=None, width=dp(28)))
            r.add_widget(text_label("%s · %s" % (k["name"], PROVIDERS[k["provider"]][0]), fg, 14))
            d = Btn(icon="delete", size_hint_x=None, width=dp(44), radius=dp(14))
            d.bind(on_release=lambda w, i=i: self.del_key(i))
            r.add_widget(d)
            g.add_widget(r)

        if len(st["keys"]) < MAX_KEYS:
            g.add_widget(title("Добавить ключ"))
            c1, self.name = field("Название")
            c2, self.key = field("API ключ", True)
            g.add_widget(c1)
            g.add_widget(c2)
            seg = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            for p, (n, _) in PROVIDERS.items():
                b = Btn(text=n, bg=DARK if p == self.prov else SOFT, fg=WHITE if p == self.prov else DARK)
                b.bind(on_release=lambda w, p=p: self.set_prov(p))
                seg.add_widget(b)
            g.add_widget(seg)
            add = Btn(icon="add", fg=WHITE, bg=DARK, size_hint_y=None, height=dp(48), radius=dp(16))
            add.bind(on_release=self.add_key)
            g.add_widget(add)

        k = self.app.cur_key()
        g.add_widget(title("Модели" + (" · " + PROVIDERS[k["provider"]][0] if k else "")))
        if k:
            for n, i in models_for(self.app, k["provider"]):
                cur = i == self.app.cur_model(k)
                b = Btn(text=n, bg=DARK if cur else CARD, fg=WHITE if cur else DARK,
                        size_hint_y=None, height=dp(46))
                b.bind(on_release=lambda w, i=i: self.app.set_model(i))
                g.add_widget(b)
            row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
            c3, self.custom = field("Свой ID модели")
            plus = Btn(icon="add", size_hint_x=None, width=dp(56), radius=dp(14))
            plus.bind(on_release=self.add_custom)
            row.add_widget(c3)
            row.add_widget(plus)
            g.add_widget(row)
        else:
            g.add_widget(text_label("Сначала добавь ключ", GRAY, 13, size_hint_y=None, height=dp(30)))
        self.add_widget(g)

    def set_prov(self, p):
        self.prov = p
        self.build()

    def add_key(self, *a):
        n, k = self.name.text.strip(), self.key.text.strip()
        if not k:
            return
        st = self.app.store.d
        st["keys"].append({"name": n or "Key %d" % (len(st["keys"]) + 1), "provider": self.prov, "key": k})
        if st["sel"] < 0:
            st["sel"] = 0
        self.app.store.save()
        self.app.chat.refresh()
        self.build()

    def del_key(self, i):
        st = self.app.store.d
        st["keys"].pop(i)
        st["sel"] = min(st["sel"], len(st["keys"]) - 1)
        self.app.store.save()
        self.app.chat.refresh()
        self.build()

    def add_custom(self, *a):
        k, m = self.app.cur_key(), self.custom.text.strip()
        if k and m:
            self.app.store.d["custom"].setdefault(k["provider"], []).append(m)
            self.app.store.save()
            self.build()


# ---------------------------------------------------------------- app
class MonoApp(App):
    def build(self):
        self.title = "Mono AI"
        self.store = Store(os.path.join(self.user_data_dir, "data.json"))
        if platform == "android":
            try:
                from android.permissions import request_permissions
                request_permissions(["android.permission.READ_EXTERNAL_STORAGE",
                                     "android.permission.READ_MEDIA_IMAGES",
                                     "android.permission.READ_MEDIA_AUDIO"])
            except Exception:
                pass
        root = BoxLayout(orientation="vertical", padding=[dp(14), dp(34), dp(14), dp(12)], spacing=dp(10))
        self.body = BoxLayout()
        self.chat = ChatView(self)
        self.settings = SettingsView(self)
        root.add_widget(self.body)

        nav = Card(size_hint_y=None, height=dp(64), bg=CARD, padding=dp(8), spacing=dp(10))
        self.b_chat = Btn(icon="chat", radius=dp(18))
        self.b_set = Btn(icon="settings", radius=dp(18))
        self.b_chat.bind(on_release=lambda *a: self.show("chat"))
        self.b_set.bind(on_release=lambda *a: self.show("settings"))
        nav.add_widget(self.b_chat)
        nav.add_widget(self.b_set)
        root.add_widget(nav)
        self.show("chat")
        return root

    def show(self, name):
        self.body.clear_widgets()
        if name == "settings":
            self.settings.build()
        self.body.add_widget(self.chat if name == "chat" else self.settings)
        self.b_chat.style(name == "chat")
        self.b_set.style(name == "settings")

    def cur_key(self):
        d = self.store.d
        return d["keys"][d["sel"]] if 0 <= d["sel"] < len(d["keys"]) else None

    def cur_model(self, k):
        return k.get("model") or PROVIDERS[k["provider"]][1][0][1]

    def select_key(self, i):
        self.store.d["sel"] = i
        self.store.save()
        self.chat.refresh()

    def set_model(self, mid):
        k = self.cur_key()
        if k:
            k["model"] = mid
            self.store.save()
            self.chat.refresh()
            if self.body.children and self.body.children[0] is self.settings:
                self.settings.build()


if __name__ == "__main__":
    MonoApp().run()
