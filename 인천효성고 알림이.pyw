import tkinter as tk
from tkinter import ttk  # 깔끔한 버튼 UI를 위해 ttk 모듈 추가
import webbrowser
import requests
import datetime
import re
import os

# ---------------------------------------------------------
# [기본 환경 설정]
# ---------------------------------------------------------
API_KEY = "3fc1427b7cc84d76845b5199e0a77500"   # 오픈 API 인증키 통합
ATPT_OFCDC_SC_CODE = "E10"   # 인천광역시교육청 코드
SD_SCHUL_CODE = "7310252"    # 인천효성고등학교 코드
CONFIG_FILE = "widget_config.txt"  # 학년/반 설정을 저장할 파일명

# ---------------------------------------------------------
# [데이터 처리 및 API 연동 함수]
# ---------------------------------------------------------
def clean_meal_text(raw_meal):
    """급식 메뉴 문자열에서 알레르기 번호 및 불필요한 문자를 정제합니다."""
    cleaned_meals = []
    for item in raw_meal.split("<br/>"):
        item = re.sub(r"[\d.*]+", "", item)
        item = re.sub(r"\(.*?\)", "", item).strip()
        if item:
            cleaned_meals.append(item)
    return cleaned_meals

def search_food_image(food_name):
    """음식 이름을 구글 이미지에 검색합니다."""
    url = f"https://www.google.com/search?q={food_name}&tbm=isch"
    webbrowser.open(url)

# ---------------------------------------------------------
# [메인 UI 클래스]
# ---------------------------------------------------------
class SchoolWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("인천효성고 멀티 알림이")
        self.root.overrideredirect(True)  # 윈도우 창 테두리 제거
        self.root.configure(bg="#FFF9E6")  # 파스텔톤 메모지 색상

        # 창 드래그 이동용 변수
        self.start_x = None
        self.start_y = None

        # 시간표와 급식을 모두 수용할 수 있도록 크기 확장
        win_width = 300
        win_height = 550
        screen_width = self.root.winfo_screenwidth()
        x_pos = screen_width - win_width - 10
        y_pos = 10
        self.root.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")

        # 저장된 설정 불러오기 및 변수 초기화 (예: '3학년', '4반' 형태로 세팅)
        saved_grade, saved_class = self.load_config()
        self.grade_var = tk.StringVar(value=f"{saved_grade}학년")
        self.class_var = tk.StringVar(value=f"{saved_class}반")

        self.top_bar = None
        self.config_frame = None
        self.content_frame = None

        self.create_base_ui()
        self.refresh_dashboard()

    def load_config(self):
        """저장된 파일에서 학년과 반을 불러옵니다. 없을 시 기본값 '3', '4'"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
                    if len(lines) >= 2:
                        return lines[0].strip(), lines[1].strip()
            except Exception:
                pass
        return "3", "4"

    def save_config(self, grade_str, class_str):
        """선택한 학년과 반에서 '학년', '반' 글자를 빼고 숫자만 파일에 저장합니다."""
        try:
            g = grade_str.replace("학년", "")
            c = class_str.replace("반", "")
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(f"{g}\n{c}")
        except Exception:
            pass

    def on_setting_change(self, *args):
        """학년/반 변경 시 호출되는 콜백 함수"""
        g = self.grade_var.get()
        c = self.class_var.get()
        self.save_config(g, c)
        self.refresh_dashboard()

    def create_base_ui(self):
        """최상단 바 및 전체 컨텐츠 프레임 생성"""
        # 1. 최상단 타이틀바
        self.top_bar = tk.Frame(self.root, bg="#FFEAA7", height=28)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)
        self.top_bar.bind("<Button-1>", self.get_pos)
        self.top_bar.bind("<B1-Motion>", self.move_window)

        title_lbl = tk.Label(self.top_bar, text="📅 인천효성고 알림이", bg="#FFEAA7", fg="#57606f", font=("Malgun Gothic", 9, "bold"))
        title_lbl.pack(side="left", padx=10)

        close_btn = tk.Button(self.top_bar, text="✕", bg="#FFEAA7", fg="#2C3E50", borderwidth=0,
                              activebackground="#FAB1A0", command=self.root.destroy, font=("Malgun Gothic", 10))
        close_btn.pack(side="right", ipadx=10, fill="y")

        # 2. 가변 컨텐츠 영역 프레임 (급식 + 설정 + 시간표 내용이 그려짐)
        self.content_frame = tk.Frame(self.root, bg="#FFF9E6")
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=(8, 8))

    def refresh_dashboard(self):
        """오늘의 급식과 현재 설정된 학년/반의 시간표 데이터를 불러와 화면에 다시 그립니다."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        today_str = datetime.datetime.today().strftime("%Y%m%d")
        weekday = datetime.datetime.today().weekday()
        
        # API 검색을 위해 '학년', '반' 글자 제거
        current_grade = self.grade_var.get().replace("학년", "")
        current_class = self.class_var.get().replace("반", "")

        # ==========================================
        # [데이터 파싱 1: 급식 정보]
        # ==========================================
        meal_list = ["오늘은 급식이 없습니다."]
        if weekday < 5:
            meal_url = "https://open.neis.go.kr/hub/mealServiceDietInfo"
            try:
                res = requests.get(meal_url, params={
                    "KEY": API_KEY, "Type": "json", "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
                    "SD_SCHUL_CODE": SD_SCHUL_CODE, "MLSV_YMD": today_str, "MMEAL_SC_CODE": "2"
                }, timeout=5).json()
                if "mealServiceDietInfo" in res:
                    meal_list = clean_meal_text(res["mealServiceDietInfo"][1]["row"][0]["DDISH_NM"])
            except Exception:
                meal_list = ["급식 정보를 불러오지 못했습니다."]
        else:
            meal_list = ["주말입니다. 푹 쉬세요!"]

        # ==========================================
        # [데이터 파싱 2: 시간표 정보]
        # ==========================================
        timetable_list = []
        error_tt = None
        if weekday < 5:
            tt_url = "https://open.neis.go.kr/hub/hisTimetable"
            try:
                res_tt = requests.get(tt_url, params={
                    "KEY": API_KEY, "Type": "json", "ATPT_OFCDC_SC_CODE": ATPT_OFCDC_SC_CODE,
                    "SD_SCHUL_CODE": SD_SCHUL_CODE, "ALL_TI_YMD": today_str,
                    "GRADE": current_grade, "CLASS_NM": current_class
                }, timeout=5).json()
                
                if "hisTimetable" in res_tt:
                    rows = res_tt["hisTimetable"][1]["row"]
                    rows = sorted(rows, key=lambda x: int(x.get("PERO", 0)))
                    timetable_list = [row["ITRT_CNTNT"] for row in rows]
                else:
                    error_tt = res_tt.get("RESULT", {}).get("MESSAGE", "등록된 시간표가 없습니다.")
            except Exception:
                error_tt = "시간표를 불러오지 못했습니다."

        # ==========================================
        # [UI 그리기 1: 급식 영역]
        # ==========================================
        meal_title = tk.Label(self.content_frame, text="🍴 오늘 급식 (메뉴 클릭시 검색)", bg="#FFF9E6", fg="#2C3E50", font=("Malgun Gothic", 11, "bold"))
        meal_title.pack(anchor="w", padx=5, pady=(0, 5))

        meal_grid = tk.Frame(self.content_frame, bg="#FFF9E6")
        meal_grid.pack(anchor="w", padx=10, fill="x")

        for i, food in enumerate(meal_list):
            row, col = i // 2, i % 2
            if "없습니다" in food or "실패" in food or "못했습니다" in food or "쉬세요" in food:
                lbl = tk.Label(meal_grid, text=food, bg="#FFF9E6", fg="#7F8C8D", font=("Malgun Gothic", 10))
                lbl.grid(row=row, column=col, sticky="w", padx=5, pady=2)
            else:
                lbl = tk.Label(meal_grid, text=food, bg="#FFF9E6", fg="#34495E", font=("Malgun Gothic", 10), cursor="hand2")
                lbl.grid(row=row, column=col, sticky="w", padx=5, pady=2)
                lbl.bind("<Button-1>", lambda e, f=food: search_food_image(f))
                lbl.bind("<Enter>", lambda e, l=lbl: l.configure(font=("Malgun Gothic", 10, "underline")))
                lbl.bind("<Leave>", lambda e, l=lbl: l.configure(font=("Malgun Gothic", 10)))

        # 두 영역을 구분하는 깔끔한 구분선
        separator = tk.Frame(self.content_frame, bg="#FFEAA7", height=1)
        separator.pack(fill="x", pady=(15, 10))

        # ==========================================
        # [UI 그리기 2: 드롭다운 버튼 영역 (구분선 아래)]
        # ==========================================
        self.config_frame = tk.Frame(self.content_frame, bg="#FFF9E6")
        self.config_frame.pack(anchor="w", padx=5, pady=(0, 10))

        # ttk.Combobox를 사용해 깔끔한 버튼형 드롭다운 생성
        grade_options = ["1학년", "2학년", "3학년"]
        grade_cb = ttk.Combobox(self.config_frame, textvariable=self.grade_var, values=grade_options, state="readonly", width=6, font=("Malgun Gothic", 10))
        grade_cb.pack(side="left", padx=(0, 10))
        grade_cb.bind("<<ComboboxSelected>>", self.on_setting_change)

        # 학교 상황에 맞춰 8반까지만 생성
        class_options = [f"{i}반" for i in range(1, 9)]
        class_cb = ttk.Combobox(self.config_frame, textvariable=self.class_var, values=class_options, state="readonly", width=6, font=("Malgun Gothic", 10))
        class_cb.pack(side="left")
        class_cb.bind("<<ComboboxSelected>>", self.on_setting_change)

        # ==========================================
        # [UI 그리기 3: 시간표 영역]
        # ==========================================
        tt_title = tk.Label(self.content_frame, text="⏰ 오늘 시간표", bg="#FFF9E6", fg="#2C3E50", font=("Malgun Gothic", 11, "bold"))
        tt_title.pack(anchor="w", padx=5, pady=(0, 5))

        tt_box = tk.Frame(self.content_frame, bg="#FFF9E6")
        tt_box.pack(anchor="w", padx=10, fill="x")

        if weekday >= 5:
            lbl = tk.Label(tt_box, text="주말에는 시간표가 없습니다.", bg="#FFF9E6", fg="#7F8C8D", font=("Malgun Gothic", 10))
            lbl.pack(anchor="w", padx=5, pady=2)
        elif error_tt:
            lbl = tk.Label(tt_box, text=error_tt, bg="#FFF9E6", fg="#7F8C8D", font=("Malgun Gothic", 10))
            lbl.pack(anchor="w", padx=5, pady=2)
        elif not timetable_list:
            lbl = tk.Label(tt_box, text="오늘은 등록된 시간표가 없습니다.", bg="#FFF9E6", fg="#7F8C8D", font=("Malgun Gothic", 10))
            lbl.pack(anchor="w", padx=5, pady=2)
        else:
            for i, subject in enumerate(timetable_list, start=1):
                lbl_text = f"{i}교시  |  {subject}"
                lbl = tk.Label(tt_box, text=lbl_text, bg="#FFF9E6", fg="#34495E", font=("Malgun Gothic", 10))
                lbl.pack(anchor="w", padx=5, pady=2)

        # ==========================================
        # [UI 그리기 4: 하단 커스텀 문구 고정]
        # ==========================================
        maker_lbl = tk.Label(self.content_frame, text="made by PYO", bg="#FFF9E6", fg="#B2BEC3", font=("Malgun Gothic", 8))
        maker_lbl.pack(side="bottom", anchor="w", pady=(5, 0))

    # ---------------------------------------------------------
    # [창 제어 마우스 이벤트 함수]
    # ---------------------------------------------------------
    def get_pos(self, event):
        self.start_x = event.x
        self.start_y = event.y

    def move_window(self, event):
        deltax = event.x - self.start_x
        deltay = event.y - self.start_y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

if __name__ == "__main__":
    app_window = tk.Tk()
    app_engine = SchoolWidget(app_window)
    app_window.mainloop()
