""""
Application pour envoyer des embeds via un bot dans un channel
donné grace à un JSON obtenu sur le site https://discohook.org
"""

import asyncio
import sys
import json
import os
import webbrowser
import subprocess

from json import JSONDecodeError
from discord import Client, Embed, LoginFailure
from typing import Optional, Union, Tuple, List
from tkinter import Button, Entry, Frame, Label, Tk, Text
from tkinter.constants import ACTIVE, DISABLED, END, LEFT, NORMAL, RIGHT, TOP

from discord.channel import CategoryChannel, VoiceChannel
from discord.errors import Forbidden, NotFound
from traceback import print_exception

if getattr(sys, 'frozen', False):
    PATH = os.path.dirname(sys.executable)
else:
    PATH = os.path.dirname(os.path.realpath(__file__))

BG_1 = "#36393F"
BG_2 = "#40444B"
FG = "#B9BBBE"
SELECT = "#718BD7"
ERROR_1 = "#FF0000"
ERROR_2 = "#FFAA00"

DEFAULT = "Une erreur est survenue"
INFO_START = "Remplir Token, Channel et Message puis appuyer sur Envoyer"
INVALID_CHANNEL = "'{channel}' n'est pas un channel valide"
EMPTY_CHANNEL = "Vous devez spécifier le channel"
EMPTY_TOKEN = "Vous devez spécifier le token"
INVALID_TOKEN = "'{token}' n'est pas un token valide"
EMPTY_MESSAGE = "Vous devez spécifier le message"
DECODE_MESSAGE = ("Erreur lors du décodage du message \n"
                  "Ligne {line}, caractère {char}")
CONTENT_MESSAGE = "Le contenu du message doit être du texte ou null"
LIST_EMBEDS = "Les embeds doivent être dans une liste ou null"
ERROR_EMBEDS = "Une erreur est survenue au {number_embed} embed"
WAIT_CONNECT = "Connexion au bot, veuillez patienter..."
NOT_FOUND_CHANNEL = "'{channel}' n'a pas été trouvé"
INVALID_TYPE_CHANNEL = "'{channel}' n'est pas un type de channel valide"
MISSING_PERMISSIONS = "Le bot manque de permissions"
WRONG_TOKEN = "Le token n'a pas permis l'authentification"
SUCCESS = "Les messages ont été envoyés avec succès"


class DebugError(Exception):
    """Representation d'une erreur."""

    def __init__(
        self,
        message: str,
        widjet: 'Field',
        ligne: int = None,
        colone: int = None
    ) -> None:

        self.message = message
        self.widjet = widjet
        self.ligne = ligne
        self.colone = colone
        super().__init__(message)


class Field(Frame):
    """Champ de text."""

    def __init__(self, root: Tk, label: str, center: bool = False,
                 frozen: bool = False, entry: bool = False) -> None:

        super().__init__(root, bg=BG_1)
        self.label = Label(self, text=label, width=8, bg=BG_1, fg=FG)
        self.center = bool(center)
        Widget = Entry if entry else Text
        self.entry = Widget(
            self,
            font=("arial", 11, "normal"),
            insertbackground=FG,
            bg=BG_2,
            fg=FG,
            borderwidth=1,
            relief="flat",
            highlightbackground=BG_1,
            highlightcolor=SELECT,
            highlightthickness=1,
            insertwidth=1
        )

        if Widget is Text:
            self.entry.configure(height=1 if label != "Debug" else 2,
                                 undo=True, wrap="none")

        if frozen:
            self.entry.configure(state=DISABLED)

        self.pos()

    @property
    def text(self) -> str:
        if isinstance(self.entry, Entry):
            return self.entry.get()
        else:
            return self.entry.get(1.0, END).strip()

    def pos(self) -> None:
        """Positionne le champs."""
        self.label.pack(side=LEFT, anchor="n")
        self.entry.pack(side=LEFT, expand=True,
                        fill="both" if self.center else "x")

        self.pack(side=TOP, expand=self.center,
                  fill="both" if self.center else "x")


class FieldsManager:
    """Manager des camps."""

    def __init__(self, app: Tk) -> None:
        self.token = Field(app, "Token", entry=True)
        self.channel = Field(app, "Channel", entry=True)
        self.message = Field(app, "Message", center=True)
        self.debug = Field(app, "Debug")
        self.all = [self.token, self.channel, self.message]

    def __iter__(self):
        return self.all.__iter__()


class Sender(Tk):
    """Application princiaple."""

    def __init__(self) -> None:
        super().__init__()

        self.minsize(width=400, height=250)
        self.geometry("700x500")
        self.title("Discord Sender")
        self.resizable(height=None, width=None)
        self.config(padx=10, pady=10, bg=BG_1)
        self.iconbitmap(PATH+"\\app.ico")
        self.sending = False
        self.fields = FieldsManager(self)

        self.send_button = Button(self, text="Envoyer",
                                  command=self.send_messages, width=10)
        self.site_button = Button(self, text="Site",
                                  command=self.open_site, width=10)

        self.send_button.pack(side=RIGHT, pady=2)
        self.site_button.pack(side=RIGHT, pady=2, padx=2)
        self.need_change: Optional[Tuple[Field, str, DebugError]] = None

        self.info(INFO_START)

    def run(self) -> None:
        self.mainloop()
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.close()

    def open_site(self) -> None:
        """Ouvre le site dans le navigateur."""
        url = "https://discohook.org"
        if sys.platform == 'win32':
            os.startfile(url)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', url])
        else:
            try:
                subprocess.Popen(['xdg-open', url])
            except OSError:
                try:
                    webbrowser.open_tab(url)
                except Exception as err:
                    self.debug(err)

    @property
    def channel(self) -> int:
        """Retourne l'id du channel si celui-ci semble valide"""
        f_channel = self.fields.channel
        channel = f_channel.text.replace(" ", "")

        try:
            channel_id = int(channel)
            if 10**15 > channel_id or channel_id > 10**19:
                raise ValueError()
        except ValueError:
            raise DebugError(
                widjet=f_channel,
                message=INVALID_CHANNEL.format(channel=channel)
                if channel else EMPTY_CHANNEL
            )

        return channel_id

    @property
    def token(self) -> str:
        """Retourne le token si celui-ci semble valide"""
        f_token = self.fields.token
        token = f_token.text.replace(" ", "")

        if not token:
            raise DebugError(
                message=EMPTY_TOKEN,
                widjet=f_token
            )
        elif len(token) < 30 or len(token) > 64:
            raise DebugError(
                message=INVALID_TOKEN.format(token=token),
                widjet=f_token
            )

        return token

    @property
    def message(self) -> Tuple[str, List[Embed]]:
        """Retourne le message et les embeds si ceux-ci semblent valides"""

        f_message = self.fields.message
        message = f_message.text

        if not message:
            raise DebugError(message=EMPTY_MESSAGE, widjet=f_message)

        try:
            data = json.loads(message)
        except JSONDecodeError as e:
            raise DebugError(
                message=DECODE_MESSAGE.format(line=e.lineno, char=e.colno),
                widjet=f_message,
                ligne=e.lineno,
                colone=e.colno
            )

        content: str = data.get("content", "")
        if not (isinstance(content, str) or content is None):
            raise DebugError(message=CONTENT_MESSAGE, widjet=f_message)

        raw_embeds: List = data.get("embeds", [])
        if not (isinstance(raw_embeds, list) or raw_embeds is None):
            raise DebugError(message=LIST_EMBEDS, widjet=f_message)
        embeds = []
        for i, raw_embed in enumerate(raw_embeds, start=1):
            try:
                embed = Embed.from_dict(raw_embed)
            except Exception:
                n = "1er" if i == 1 else f"{i}ème"
                raise DebugError(message=ERROR_EMBEDS.format(number_embed=n),
                                 widjet=f_message)
            embeds.append(embed)

        return content, embeds

    @property
    def vars(self) -> Tuple[str, int, str, List[Embed]]:
        """Retourne : token, channel_id, message, embeds"""
        return self.token, self.channel, *self.message

    def send_messages(self) -> None:
        """Envoye le message et verifie si il est valide"""
        if self.sending:
            print("Already sending, ignored")
            return

        self.lock_send()
        try:
            if self.need_change:
                if self.need_change[0].text == self.need_change[1]:
                    raise self.need_change[2]
            args = self.vars
            self.info(WAIT_CONNECT)

            def _callback_send():
                try:
                    self._send(*args)
                except Exception as err:
                    self.debug(err)
                finally:
                    self.after(1000, self.unlock_send)
            self.after(200, _callback_send)

        except DebugError as err:
            self.debug(err)
            self.unlock_send()

    def lock_send(self):
        """Bloque le bouton d'envoie."""
        self.sending = True
        self.send_button.config(state=DISABLED)

    def unlock_send(self):
        """Debloque le bouton d'envoie."""
        self.sending = False
        self.send_button.config(state=ACTIVE)

    def _send(
        self, token: str, channel: int, content: str, embeds: List[Embed]
    ) -> None:
        """Envoie le messsage."""
        error = None
        bot = Client()

        @bot.event
        async def on_ready():
            nonlocal error

            target_channel = bot.get_channel(channel)
            if target_channel is None:
                error = DebugError(
                    message=NOT_FOUND_CHANNEL.format(channel=channel),
                    widjet=self.fields.channel
                )
                return await bot.logout()
            elif isinstance(target_channel, (CategoryChannel, VoiceChannel)):
                error = DebugError(
                    message=INVALID_TYPE_CHANNEL.format(channel=channel),
                    widjet=self.fields.channel
                )
                return await bot.logout()

            try:
                if content and len(embeds) == 1:
                    await target_channel.send(content, embed=embeds[0])
                else:
                    if content:
                        await target_channel.send(content)
                    for embed in embeds:
                        await target_channel.send(embed=embed)
            except Forbidden as err:
                error = DebugError(
                    message=MISSING_PERMISSIONS,
                    widjet=self.fields.message
                )
            except NotFound as err:
                error = DebugError(
                    message=NOT_FOUND_CHANNEL.format(channel=channel),
                    widjet=self.fields.message
                )
            except Exception as err:
                print("Ignored exception:")
                error = err
            finally:
                await bot.logout()

        try:
            loop = asyncio.get_event_loop()
            try:
                loop.run_until_complete(bot.start(token))
            except KeyboardInterrupt:
                loop.run_until_complete(bot.logout())
        except LoginFailure:
            raise DebugError(message=WRONG_TOKEN, widjet=self.fields.token)

        if error:
            raise error
        else:
            self.clear_error()
            self.info(SUCCESS)

    def debug(self, error: Union[Exception, DebugError]) -> None:
        """Affiche l'erreur dans le champ d'erreur."""
        print("Catched Exception:")
        print_exception(type(error), error, error.__traceback__)
        self.clear_error()
        if isinstance(error, DebugError):
            self.info(error.message)
            error.widjet.entry.config(highlightcolor=ERROR_2,
                                      highlightbackground=ERROR_1)
            self.need_change = (error.widjet, error.widjet.text, error)
        else:
            self.info(str(error))
            self.need_change = None

    def clear_error(self):
        """Met la couleur par defaut de tous les champs."""
        for f in self.fields.all:
            f.entry.config(highlightcolor=SELECT, highlightbackground=BG_1)

    def info(self, text: str) -> None:
        """Affiche le text dans le champ debug."""
        entry = self.fields.debug.entry
        entry.configure(state=NORMAL)
        entry.delete(1.0, END)
        entry.insert(END, text)
        entry.configure(state=DISABLED)


if __name__ == "__main__":
    s = Sender()
    s.run()
