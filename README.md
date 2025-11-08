# python-
一帮营销号天天吹的弹窗爱心，弹窗祝福，现在他来了
通过把屏幕按照自定义变量的大小进行分为像素块
把字符转为点阵图，然后映射到屏幕的实际坐标
理论支持所有字符和文字
如果乱码，需要自己找字体
自我感觉我的注释应该挺清晰的
实在不清楚的我也让ai给出注释了
总之自己悟吧
先安装运行库
python -m pip install --upgrade Pillow

查找下面的内容然后修改
apply_config 这个函数里面的东西
以下是所有参数


在这里定义出现的窗口内容和样式
            # ======== 可调参数 ========
        CELL_SIZE=20,            # 网格单元像素（越小越细腻，但点/窗口数↑、更吃性能）
        Kuan_SIZE=100,           # 小窗口宽（像素）——窗口模式用
        DOT_SIZE=30,             # 小窗口高（像素）——窗口模式用
        GRID_MARGIN=1,           # 网格留白（单位：网格单元），四周空出这么多格
        MAX_WINDOWS=20000,       # 窗口数量上限（防卡顿）
        
        SHOW_WINDOWS=True,       # 是否显示提示窗口（窗口模式是否真的弹窗）
        SHOW_BORDER=False,       # 窗口是否带边框（True=正常窗口；False=无边框气泡）
        Display_text=True,       # 窗口内是否显示文字（从 tips 随机抽）
        Custom_colors=False,     # 是否使用自定义 bg_colors（False=用内置彩色）

        # 仅在 SHOW_BORDER=True 时生效（窗口模式）
        FORBID_OVERLAP=True,     # 禁止窗口重叠/“相碰”
        MIN_GAP_PX=0,            # 窗口之间最小间距（像素），FORBID_OVERLAP=True 时有效

        DISPLAY_ORDER=1,         # 生成顺序：0左→右 1右→左 2上→下 3下→上 4中心→外
        TWO_LINES_TOGETHER=False,# 两行是否一起生成：True一起；False先上行后下行

        # ======== 生成速度 & 完成后等待（两种模式通用） ========
        GEN_INTERVAL_MS=1,       # 基础生成间隔（毫秒），越小越快；0≈几乎瞬间
        GEN_JITTER_MS=0,         # 生成间隔的随机抖动范围 0~JITTER（毫秒）；0=不抖动
        HOLD_AFTER_DONE_MS=10000,# 整段完全生成后保留多久再消失（毫秒）

        # ======== 粒子模式与特效 ========
        PARTICLE=False,          # True=使用粒子替代窗口；False=窗口模式
        PARTICLE_SINGLE_STEP=True,# 粒子每tick生成策略：True=1个；False=一批
        PARTICLE_BATCH_SIZE=8,   # 批量模式每tick粒子数（SINGLE_STEP=False 时生效）
        PARTICLE_DOT_RADIUS=2,   # 粒子半径（像素）
        PARTICLE_LINE_WIDTH=2,   # 同连通块路径线宽（像素）
        PARTICLE_COLOR_CHANGE_MS=10, # 粒子颜色随机切换周期（毫秒），颜色来自 bg_colors
        PARTICLE_BG="#000000",   # 画布背景色（不用透明时）

        # —— 透明画布（仅 Windows 真正透明，其它平台自动回退不透明）——
        TRANSPARENT_CANVAS=True, # True=启用色键透明；False=用 PARTICLE_BG
        TRANSPARENT_COLOR="#00FF00", # 色键（不要与粒子颜色重复，否则会被“抠掉”）

        # 跨“无坐标区”桥接（不同连通块之间的连接线）
        SHOW_PARTICLE_BRIDGE=False,   # 是否绘制连通块之间的桥接线（跨空白）
        PARTICLE_BRIDGE_DASH=(6, 4),  # 虚线样式 (线段长度, 空段长度)；None=实线
        PARTICLE_BRIDGE_WIDTH=1,      # 桥接线宽（像素）

        # 扩散火花特效
        PARTICLE_SPARKS=True,     # 是否启用粒子扩散火花
        PARTICLE_SPARK_COUNT=3,   # 每个粒子喷射的火花数量
        PARTICLE_SPARK_STEPS=10,  # 火花寿命（步数/帧数）
        PARTICLE_SPARK_SPEED_PX=2.0,# 火花每步外扩像素
        PARTICLE_SPARK_RADIUS=3,  # 火花初始半径（逐帧衰减）

        # ======== 文本与配色 ========
        text="文字",            # 要渲染的文本（支持换行、符号、emoji 等）
        tips=[
            '好好吃饭','好好休息','早点休息','天天开心','记得喝水','按时吃饭','别熬夜了','照顾好自己',
            '注意身体','记得运动','放松一下','保持微笑','劳逸结合','别太劳累','记得午休','多吃水果',
            '出去走走','呼吸新鲜空气','保持好心情','别久坐','记得早餐','保护眼睛','注意保暖','别着凉',
            '保持健康','平安喜乐','开心每一天','一切顺利','万事如意','心想事成'
        ],                         # 窗口模式 Label 文案池（Display_text=True 时使用）
        bg_colors=['#ffffff'],     # 颜色池：窗口背景色/粒子颜色随机从此选择
        # ======== 兼容保留（当前实现不使用，可忽略） ========
        BG_COLOR="#111111",       # 旧版根背景色（兼容）
        DOT_COLORS=["#ffffff"],   # 旧版点颜色（兼容）
        
        
        ### RANDOM_WINDOW_COUNT  =  X  X是随机窗口数
    """
