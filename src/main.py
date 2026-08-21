import flet as ft
import asyncio
import json

from functions.hash_pass import hash_password, check_password
from functions.requests import get_user_request, search_users, get_messages_chat, get_chat_list_request, create_direct_chat_request
from functions.other import make_handler
from database import create_db, User, Chat, ChatMember, Message, Attachment, AttachmentType, ChatType
from crud import create_user, get_user_by_email, create_new_message
import websockets


THEME_COLOR1 = "#404040"
THEME_COLOR2 = "#E0E0E0"

_MAIN_FONT = rf"D:\\Fonts\\mikron font.otf"



async def main(page: ft.Page):
    page.title = "MANSI Messenger"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 0
    page.fonts = {"Mikron Font": _MAIN_FONT}

    await create_db()

    def show_main_app(my_id: int):
        page.controls.clear()
        page.title = "MANSI Messenger"
        background = ft.Container(
            expand=True,
            bgcolor="#f4f0fa"
        )

        cur_chat_id: int = None
        receiver_id: int = None
        cur_ws = None
        
        async def connect_to_websocket(user_id: int):
            nonlocal cur_ws
            url = f"ws://127.0.0.1:8000/ws/user?user_id={user_id}"
            async with websockets.connect(url) as ws:
                cur_ws = ws  
                while True:
                    payload = json.loads(await ws.recv())
                    if payload["type"] == "message":
                        await draw_message(payload)
                    elif payload["type"] == "chat_created":
                        await draw_chat(payload)
        
        asyncio.create_task(connect_to_websocket(user_id=my_id))
        
        async def draw_message(payload: dict):
            message = payload["message"]
            if message["sender_id"] == my_id:
                msg_container = ft.Container(content=ft.Text(value=f"Я: {message["content"]}", color=THEME_COLOR2),
                                            margin=ft.Margin.only(top=50, bottom=50), padding=10, border_radius=14, width=200, bgcolor=THEME_COLOR1)
                user_chat.controls.append(ft.Row(controls=[msg_container], alignment=ft.CrossAxisAlignment.END))
            else:
                if cur_chat_id == message["chat_id"]:
                    msg_container = ft.Container(content=ft.Text(value=f"{message["sender_username"]}: {message["content"]}", color=THEME_COLOR2),
                                                margin=ft.Margin.only(top=50, bottom=50), padding=10, border_radius=14, width=200, bgcolor=THEME_COLOR1)
                    user_chat.controls.append(ft.Row(controls=[msg_container], alignment=ft.CrossAxisAlignment.START))
            page.update()

        async def draw_chat(payload: dict):
            chat = payload["chat"]
            receiver_btn = ft.Button(content=ft.Row(expand=True,
                        controls=[
                                ft.Text(value=chat["title"], size=20, color=THEME_COLOR2)]),
                                bgcolor=THEME_COLOR1, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=0)), on_click=make_handler(open_chat, chat=chat))
            receiver_container = ft.Column(controls=[ft.Container(content=receiver_btn, height=70)], expand=True)
            chats_view.controls.append(receiver_container)
            page.update()


        async def update_chats():
            chats = await get_chat_list_request(user_id=my_id)
            for chat in chats:
                await draw_chat(payload={
                    "chat": chat
                })
            page.update()

        asyncio.create_task(update_chats())


        # Каждые 3 секунды обновляем список чатов у пользователя
        #async def handle_chats(e):
        #    try:
        #        while True:
        #            chats_view.controls.clear()
        #            chats = await get_chat_list_request(user_id=my_id) # OK
        #            for chat in chats:
        #                receiver_btn = ft.Button(content=ft.Row(expand=True,
        #                    controls=[
        #                        ft.Text(value=chat["title"], size=20, color=THEME_COLOR2),
        #                    ]), bgcolor=THEME_COLOR1, style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=0)), on_click=make_handler(open_chat, chat=chat)
        #                )
        #                receiver_container = ft.Column(controls=[ft.Container(content=receiver_btn, height=70)], expand=True)
        #                chats_view.controls.append(receiver_container)
        #            page.update()
        #            await asyncio.sleep(3)
        #    except asyncio.CancelledError:
        #        raise
        
        # функция переключения видимости search_container и search_input
        async def toggle_search(e):
            if search_container.visible:
                search_container.visible = False
                search_input.visible = False
                chats_view_container.visible = True     
                page.appbar.leading_width = 110
                search_results.controls.clear()
            else:
                search_container.visible = True
                search_input.visible = True
            search_input.value = ""
            leading_row.controls.remove(search_input)
            page.update()
         
        # Ловим сообщения каждые 3 секунды, отображаем отправителю и получателю
        #async def handle_message(e, chat_id: int):
        #    try:
        #        while True:
        #            user_chat.controls.clear()
        #            messages = await get_messages_chat(chat_id) # OK
        #            for msg in messages:
        #                if msg["sender_id"] == my_id:
        #                    msg_container = ft.Container(content=ft.Text(value=f"Я: {msg["content"]}", color=THEME_COLOR2),
        #                                            margin=ft.Margin.only(top=50, bottom=50), padding=10, border_radius=14, width=200, bgcolor=THEME_COLOR1)
        #                    user_chat.controls.append(ft.Row(controls=[msg_container], alignment=ft.CrossAxisAlignment.END))
        #                else:
        #                    sender = await db_get(class_=User, uid=msg["sender_id"]) # прямой вызов CRUD
        #                    msg_container = ft.Container(content=ft.Text(value=f"{sender.username}: {msg["content"]}", color=THEME_COLOR2),
        #                                            margin=ft.Margin.only(top=50, bottom=50), padding=10, border_radius=14, width=200, bgcolor=THEME_COLOR1)
        #                    user_chat.controls.append(ft.Row(controls=[msg_container], alignment=ft.CrossAxisAlignment.START))
        #            page.update()
        #            await asyncio.sleep(3)
        #    except asyncio.CancelledError:
        #        raise
        
        
        # Создание чата -> запуск Task -> добавление сообщения в БД / добавление сообщения в БД (old)
        # Создание чата DIRECT -> добавление участников -> отправка json на сервер
        async def on_send(e):
            nonlocal cur_chat_id, receiver_id, cur_ws
            if cur_chat_id is None:
                # chat = await create_chat(name=None, type_=ChatType.DIRECT) # прямой вызов CRUD
                # await add_members_to_chat_direct(chat_id=chat.id, uid1=my_id, uid2=receiver_id) # прямой вызов CRUD
                data = await create_direct_chat_request(user_ids=[my_id, receiver_id]) # создаем DIRECT чат
                chat = data["chat"]
                user = await get_user_request(user_id=receiver_id)
                await draw_chat(payload={"chat": {"chat_id": chat["id"], "receiver_id": receiver_id, "title": user["username"]}})
                cur_chat_id = chat["id"]
            await cur_ws.send(
                json.dumps({
                    "type": "message",
                    "chat_id": cur_chat_id,
                    "content": user_input.value,
                })
            )
            user_input.value = ""
            page.update()

        # Отображаем новый чат (НЕ СОЗДАЕМ!!!)
        async def start_chat(e, user_id: int):
            await toggle_search(e) # переключаем видимость search_container и search_input обратно на chats_view_container
            user = await get_user_request(user_id=user_id)
            nonlocal cur_chat_id, receiver_id
            receiver_id = user_id
            cur_chat_id = None
            user_chat.controls.clear()
            user_name.value = user["username"]
            user_chat_stack.visible = True
            page.update()
        
        # Отображаем уже существующий чат
        async def open_chat(e, chat: dict):
            nonlocal cur_chat_id, receiver_id
            receiver_id = chat["receiver_id"]
            cur_chat_id = chat["chat_id"]
            user_name.value = chat["title"]

            user_chat_stack.visible = True
            user_chat.controls.clear()

            message_history = await get_messages_chat(cur_chat_id)
            for message in message_history:
                await draw_message(payload={
                    "message": message,
                })

            page.update()


        search_results = ft.ListView()
        
        # Показывает в поиске пользователей, username которых соответствует запросу
        async def on_search(e):
            query = search_input.value.strip()
            if query:
                users = await search_users(query=query, my_id=my_id) # OK
                search_results.controls.clear()
                for user in users:
                    btn = ft.TextButton(
                        content=ft.Column(
                            controls=[ft.Container(content=ft.Text(value=user["username"], color=THEME_COLOR2, size=15)),
                                      ft.Container(content=ft.Text(value=f"online", color=THEME_COLOR2, size=12))],
                                alignment=ft.MainAxisAlignment.CENTER,
                                horizontal_alignment=ft.CrossAxisAlignment.START,
                                margin=ft.Margin.only(left=10, right=10)
                            ),
                        height=60,
                        style=ft.ButtonStyle(color=THEME_COLOR1, bgcolor="#202020", alignment=ft.Alignment.CENTER_LEFT, shape=ft.RoundedRectangleBorder(radius=0)),
                        on_click=make_handler(start_chat, user_id=user["id"])
                    )
                    search_results.controls.append(btn)
                chats_view_container.visible = False
                search_container.visible = True
            else:
                chats_view_container.visible = True
                search_container.visible = False
            page.update()

        search_container = ft.Container(
            content=search_results,
            width=350,
            bgcolor=THEME_COLOR1, opacity=0.9,
            visible=False,
        )

        search_input = ft.TextField(
            value='', hint_text="Поиск...",
            width=300, height=40,
            text_style=ft.TextStyle(color=THEME_COLOR2, font_family="Mikron Font"),
            hint_style=ft.TextStyle(color="white54", font_family="Mikron Font"),
            border=5, border_color=THEME_COLOR2,
            content_padding=ft.Padding.only(bottom=10),
            on_change=on_search
        )
        
        # Нажатие на иконку ПОИСК
        async def search_icon_clicked(e):
            search_input.visible = True
            if search_input not in leading_row.controls:
                leading_row.controls.append(search_input)
                page.appbar.leading_width = 400
                search_container.visible = True
                chats_view_container.visible = False
                page.update()
                await search_input.focus()
            else:
                leading_row.controls.remove(search_input)
                page.appbar.leading_width = 110
                search_container.visible = False

                chats_view_container.visible = True
                search_results.controls.clear()
                page.update()


        bar_shadow = ft.BoxShadow(
            blur_radius=12,
            color="#00000030",
            offset=ft.Offset(0, 3),
        ),
                
        leading_row = ft.Row(controls=[
                    ft.Container(
                        content=ft.IconButton(ft.Icons.SEARCH_ROUNDED, icon_color=THEME_COLOR2, margin=ft.Margin.only(left=5), on_click=search_icon_clicked),
                        border_radius=999, shadow=bar_shadow
                    )
                ]
            )
        
        page.appbar = ft.AppBar(
            leading=leading_row,
            leading_width=110,
            center_title=True,
            bgcolor="#5a5661",
            actions=[
                ft.Container(
                    content=ft.IconButton(ft.Icons.MENU, icon_color=THEME_COLOR2, margin=ft.Margin.only(left=5)),
                    border_radius=999, shadow=bar_shadow
                ),
                ft.Container(
                    content=ft.IconButton(ft.Icons.PERSON, icon_color=THEME_COLOR2, margin=ft.Margin.only(right=5)),
                    border_radius=999, shadow=bar_shadow
                ),
            ],
        )

        chats_view = ft.ListView(controls=[], expand=True, spacing=10, padding=10, margin=ft.Margin.only(bottom=60))
        chats_view_container = ft.Container(
            content=chats_view, 
            width=300, border=ft.Border.only(right=ft.BorderSide(1, color="#404040")),
            bgcolor=THEME_COLOR1,
            visible=True,
        )


        user_name = ft.Text(value="-", size=15, opacity=1, color="#E4E4E4")
        user_info = ft.Button(content=ft.Container(content=user_name, alignment=ft.Alignment.CENTER_LEFT, padding=ft.Padding.symmetric(horizontal=10)),
                            color=THEME_COLOR2, bgcolor="#5a5661")
        user_chat = ft.ListView(spacing=10, padding=10)
    
        send_btn = ft.IconButton(icon=ft.Icons.TELEGRAM, icon_color=THEME_COLOR2, icon_size=35, alignment=ft.Alignment.CENTER, on_click=on_send)
        user_input = ft.TextField(value='', bgcolor=THEME_COLOR1, hint_text="Введите сообщение...", opacity=0.7, suffix=send_btn, on_submit=on_send)
        

        user_info_container = ft.Container(
            content=user_info,
            height=60, expand=True,
            border_radius=3,
            opacity=0.7,
        )
       
        cur_user_params = ft.IconButton(icon=ft.Icons.SETTINGS, icon_color=THEME_COLOR2, bgcolor="#5a5661", opacity=0.7, height=50, width=50)

        cur_user_row = ft.Row(
            controls=[user_info_container, cur_user_params],
            margin=ft.Margin.only(top=5, left=10, right=10)
        )
    
        user_chat_container = ft.Container(
            expand=True,
            content=user_chat,
        )
    
        user_input_container = ft.Container(
            content=user_input,
            bgcolor="#5a5661",
            bottom=20,
            left=20,
            right=20,
            height=50,
            border_radius=14,
            opacity=0.5,
            shadow=ft.BoxShadow(
                blur_radius=18,
                color="#00000025",
                offset=ft.Offset(0, 4),
            ),
        )

        user_chat_stack = ft.Stack(
            expand=True,
            visible=False,
            controls=[
                user_chat_container,
                cur_user_row,
                user_input_container,
            ]
        )

    
        page.add(
            ft.Stack(
                expand=True,
                controls=[
                    background,
                    ft.Row(
                        expand=True,
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Stack(
                                controls=[
                                    chats_view_container,
                                    search_container
                                ]
                            ),
                            user_chat_stack
                        ]
                    ),
                ]
            )
        )
    
    def show_registration():
        page.controls.clear()
        page.title = "MANSI Messenger"
        page.window.resizable = False
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.MainAxisAlignment.CENTER
        page.bgcolor = ft.Colors.TRANSPARENT
        page.decoration = ft.BoxDecoration(
            image=ft.DecorationImage(
                src="D:\\Загрузки\\bg.gif",
                fit=ft.BoxFit.COVER,
                opacity=0.3
            )
        )
    

        welcome = ft.Text(value="Приветствуем вас! Регистрируемся?", size=30, color=THEME_COLOR2, font_family="Mikron Font")

        username_field = ft.TextField(value='', hint_text="Имя пользователя", bgcolor=THEME_COLOR1, color=THEME_COLOR2, width=300)
        email_field = ft.TextField(value='', hint_text="Email", bgcolor=THEME_COLOR1, color=THEME_COLOR2, width=300)
        password_field = ft.TextField(value='', hint_text="Пароль", bgcolor=THEME_COLOR1, color=THEME_COLOR2, width=300)
        
        # Регистрация нового пользователя
        async def register_btn_clicked(e):
            if username_field.value and email_field.value and password_field.value:
                hashed_password = hash_password(raw=password_field.value)
                user = await create_user(username=username_field.value, email=email_field.value, password_hash=hashed_password) # прямой вызов CRUD
                show_main_app(my_id=user.id)
        
        register_btn = ft.Button(
            on_click=register_btn_clicked,
            width=50,
            height=50, 
            bgcolor=THEME_COLOR1, color=THEME_COLOR2, icon=ft.Icons.CHECK_BOX, content=''
        )

        reg_form = ft.Column(controls=[username_field, email_field, password_field, register_btn], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)


        login_email = ft.TextField(hint_text="Email", bgcolor=THEME_COLOR1, color=THEME_COLOR2, width=300)
        login_password = ft.TextField(hint_text="Пароль", bgcolor=THEME_COLOR1, color=THEME_COLOR2, width=300, password=True)
        
        # Вход пользователя
        async def login_btn_clicked(e):
            if login_email.value and login_password.value:
                user = await get_user_by_email(email=login_email.value) # прямой вызов CRUD
                if check_password(uinput=login_password.value, hashed_password=user.password_hash):
                    show_main_app(my_id=user.id)
                

        login_btn = ft.Button(
            content="Войти",
            on_click=login_btn_clicked,
            bgcolor=THEME_COLOR1,
            color=THEME_COLOR2
        )

        login_form = ft.Column(
            controls=[login_email, login_password, login_btn],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15
        )


        forms_stack = ft.Stack(
            expand=True,
            controls=[reg_form, login_form]
        )

        reg_form.visible = True
        login_form.visible = False

        is_login_mode = False

        # Переключает видимости форм регистрации/входа
        def toggle_forms(e):
            nonlocal is_login_mode
            is_login_mode = not is_login_mode
            reg_form.visible = not is_login_mode
            login_form.visible = is_login_mode
            welcome.value = "Приветствуем вас снова! Логинимся?" if is_login_mode else "Приветствуем вас! Регистрируемся?"
            toggle_btn.content = "Зарегистрироваться" if is_login_mode else "Войти в аккаунт"
            page.update()

        toggle_btn = ft.Button(
            content="Войти в аккаунт",
            on_click=toggle_forms,
            bgcolor=THEME_COLOR1,
            color=THEME_COLOR2
            )

        data = ft.Column(
            controls=[toggle_btn, welcome, forms_stack],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15
        )

        data_container = ft.Container(
            expand=True, content=data, alignment=ft.Alignment.CENTER, margin=ft.Margin.only(top=150)
        )

        page.add(data_container)

        page.update()
    
    #show_main_app(my_id=0)
    show_registration()
    

asyncio.run(ft.app_async(target=main))
