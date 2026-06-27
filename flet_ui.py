import flet as ft
import flet_charts as fch
import asyncio
from datetime import datetime, timedelta
from main_agent import MainAgent
from db_agent import DatabaseAnalyst
from utils import get_stats_for_period

main_agent = MainAgent()
analyst_agent = DatabaseAnalyst(db_path='./data/screen_time.db')

async def main(page: ft.Page):
    page.title = 'DROID R407'
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1300
    page.window.height = 850
    page.window.minimum_width = 1000
    page.window.minimum_height = 700
    page.padding = 15

    # --- 1. ФУНКЦИИ ОТРИСОВКИ ---
    def create_flet_barchart(db_data):
        if not db_data:
            return ft.Container(
                content=ft.Text("Нет данных за этот период 🤷‍♂️", color=ft.Colors.GREY_500),
                alignment=ft.Alignment.CENTER,
                expand=True
            )

        chart_groups = []
        x_labels = []

        for index, (app_name, minutes) in enumerate(db_data):
            # Заменили ft на fch
            rod = fch.BarChartRod(
                to_y=minutes,
                color=ft.Colors.BLUE_900,
                width=35,
                border_radius=5,
                tooltip=f"{app_name}\n{minutes} мин."
            )
            # Заменили ft на fch
            chart_groups.append(fch.BarChartGroup(x=index, rods=[rod]))
            
            short_name = app_name[:10] + ".." if len(app_name) > 10 else app_name
            # Заменили ft на fch
            x_labels.append(
                fch.ChartAxisLabel(
                    value=index,
                    label=ft.Container(
                        content=ft.Text(short_name, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_300, ),
                        padding=ft.Padding.only(top=10)
                    )
                )
            )

        # Заменили ft на fch
        chart = fch.BarChart(
            groups=chart_groups,
            bottom_axis=fch.ChartAxis(labels=x_labels, label_size=40),
            interactive=True,
            expand=True
        )
        return chart

    chart_container = ft.Container(
        content=ft.ProgressRing(), 
        alignment=ft.Alignment.CENTER,
        expand=True
    )

    # --- 2. ЛОГИКА ОБНОВЛЕНИЯ ГРАФИКА ---
    async def update_chart(e):
        period = date_filter.value
        today = datetime.now().strftime('%Y-%m-%d')
        
        if period == "today":
            start_date = today
        else:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        data = await asyncio.to_thread(get_stats_for_period, start_date, today)
        chart_container.content = create_flet_barchart(data)
        page.update()

    # --- 3. UI КОМПОНЕНТЫ ---
    date_filter = ft.Dropdown(
        width=200,
        label="Период",
        options=[
            ft.dropdown.Option("today", "Сегодня"),
            ft.dropdown.Option("week", "Последние 7 дней"),
        ],
        value="today"
    )
    date_filter.on_change = update_chart

    dashboard_content = ft.Column(
        controls=[
            ft.Text("Панель мониторинга активности", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
            ft.Row([ft.Text(f"Данные на: {datetime.now().strftime('%d.%m.%Y')}", size=14, color=ft.Colors.GREY_400), date_filter], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=20, color=ft.Colors.ON_SURFACE_VARIANT),
            chart_container
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
    
    # --- 4. ЧАТ И ИИ ---
    chat_history = ft.ListView(expand=True, spacing=10, auto_scroll=True, padding=10)

    async def send_message(e):
        user_text = chat_input.value.strip()
        if not user_text:
            return
        
        chat_history.controls.append(
            ft.Container(
                content=ft.Text(f"Вы: {user_text}", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.BLUE_GREY_900,
                padding=10,
                border_radius=8,
                alignment=ft.Alignment.CENTER_LEFT
            )
        )
        chat_input.value = "" 
        page.update() 

        thinking_bubble = ft.Container(
            content=ft.Text("R-407 напрягает свои микросхемы...", italic=True, color=ft.Colors.GREEN_400),
            padding=10,
            alignment=ft.Alignment.CENTER_LEFT
        )
        chat_history.controls.append(thinking_bubble)
        page.update()

        try:
            decision = await asyncio.to_thread(main_agent.get_routing_decision, user_text)
            
            if decision == 'DB':
                sql_query = await asyncio.to_thread(main_agent.translate_for_db_agent, user_text)
                raw_data = await asyncio.to_thread(analyst_agent.get_data, sql_query)
                ai_answer = await asyncio.to_thread(main_agent.answer, user_text, str(raw_data))
            else:
                ai_answer = await asyncio.to_thread(main_agent.answer, user_text, "Данные БД не требуются.")
                
        except Exception as err:
            ai_answer = f"Критическая ошибка систем: {err}"

        chat_history.controls.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text("🤖 R-407:", weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400, size=12),
                        ft.Markdown(
                            value=ai_answer,
                            selectable=True,
                            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                            code_theme="atom-one-dark",
                        )
                    ],
                    spacing=5
                ), 
                bgcolor=ft.Colors.GREEN_900, 
                padding=12, 
                border_radius=8
            )
        )
        page.update()

    chat_input = ft.TextField(
        hint_text="Команда для R-407...", expand=True, border_color=ft.Colors.ON_SURFACE_VARIANT, on_submit=send_message 
    )
    send_button = ft.IconButton(icon=ft.Icons.SEND_ROUNDED, icon_color=ft.Colors.BLUE_900, on_click=send_message)

    chat_panel = ft.Container(
        content=ft.Column(
            controls=[
                ft.Row([ft.Icon(ft.Icons.ANDROID_ROUNDED, color=ft.Colors.GREEN_400), ft.Text("Дроид R-407", size=18, weight=ft.FontWeight.BOLD)], alignment=ft.MainAxisAlignment.START),
                ft.Divider(height=10, color=ft.Colors.ON_SURFACE_VARIANT),
                chat_history,
                ft.Row(controls=[chat_input, send_button], spacing=10)
            ], expand=True
        ),
        expand=2, 
        padding=15,
        bgcolor=ft.Colors.SURFACE,
        border_radius=12,
        border=ft.Border.all(1, ft.Colors.ON_SURFACE_VARIANT)
    )
    
    main_layout = ft.Row(controls=[analytics_panel, chat_panel], expand=True, spacing=15)
    page.add(main_layout)

    await update_chart(None)

if __name__ == "__main__":
    ft.run(main)