import flet as ft
import asyncio
from datetime import datetime

async def main(page: ft.Page):
    page.title = 'Title'
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1300
    page.window.height = 850
    page.window.minimum_width = 1000
    page.window.minimum_height = 700
    page.padding = 15

    dashboard_content = ft.Column(
        controls=[
            ft.Text("Панель мониторинга активности", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_400),
            ft.Text(f"Данные на: {datetime.now().strftime('%d.%m.%Y')}", size=14, color=ft.Colors.GREY_400),
            ft.Divider(height=20, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Container(
                content=ft.Text("Здесь будут графики, диаграммы и Топ программ", color=ft.Colors.GREY_500),
                alignment=ft.Alignment.CENTER,
                expand=True,
                border=ft.Border.all(1, ft.Colors.ON_SURFACE_VARIANT),
                border_radius=10,
                bgcolor=ft.Colors.BLACK12,
            )
        ],
        expand=True,
        spacing=10
    )

    analytics_panel = ft.Container(
        content=dashboard_content,
        expand=3,
        padding=20,
        bgcolor=ft.Colors.SURFACE,
        border_radius=12,
        border=ft.Border.all(1, ft.Colors.ON_SURFACE_VARIANT)
    )
    
    chat_history = ft.ListView(
        expand=True,
        spacing=10,
        auto_scroll=True,
        padding=10
    )

    # Функция обработки отправки сообщений 
    async def send_message(e):
        user_text = chat_input.value.strip()
        if not user_text:
            return
        
        # 1. Отображаем сообщение пользователя
        chat_history.controls.append(
            ft.Container(
                content=ft.Text(f"Вы: {user_text}", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.BLUE_GREY_900,
                padding=10,
                border_radius=8,
                alignment=ft.Alignment.CENTER_LEFT
            )
        )
        chat_input.value = "" # Очищаем поле ввода
        page.update() 

        # 2. Индикатор загрузки
        thinking_bubble = ft.Container(
            content=ft.Text("R-407 подгружает нейросети...", italic=True, color=ft.Colors.GREEN_400),
            padding=10,
            alignment=ft.Alignment.CENTER_LEFT
        )
        chat_history.controls.append(thinking_bubble)
        page.update()

        # 3. Имитируем задержку локальной LLM
        await asyncio.sleep(2) 
        
        # Удаляем индикатор загрузки и выводим ответ
        chat_history.controls.pop() 
        chat_history.controls.append(
            ft.Container(
                content=ft.Text(f"R-407: Обработал твой запрос. База SQLite доступна.", color=ft.Colors.GREEN_100),
                bgcolor=ft.Colors.GREEN_900,
                padding=10,
                border_radius=8,
                alignment=ft.Alignment.CENTER_LEFT
            )
        )
        

    chat_input = ft.TextField(
        hint_text="Команда для R-407...",
        expand=True,
        border_color=ft.Colors.ON_SURFACE_VARIANT,
        on_submit=send_message 
    )

    send_button = ft.IconButton(
        icon=ft.Icons.SEND_ROUNDED,
        icon_color=ft.Colors.BLUE_400,
        on_click=send_message
    )

    chat_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    [
                        ft.Icon(ft.Icons.ANDROID_ROUNDED, color=ft.Colors.GREEN_400),
                        ft.Text("Дроид R-407", size=18, weight=ft.FontWeight.BOLD)
                    ],
                    alignment=ft.MainAxisAlignment.START
                ),
                ft.Divider(height=10, color=ft.Colors.ON_SURFACE_VARIANT),
                chat_history,
                ft.Row(
                    controls=[chat_input, send_button],
                    spacing=10
                )
            ],
            expand=True
        ),
        expand=1,
        padding=15,
        bgcolor=ft.Colors.SURFACE,
        border_radius=12,
        border=ft.Border.all(1, ft.Colors.ON_SURFACE_VARIANT)
    )
    
    main_layout = ft.Row(
        controls=[analytics_panel, chat_panel],
        expand=True,
        spacing=15
    )

    page.add(main_layout)

if __name__ == "__main__":
    ft.run(main)
