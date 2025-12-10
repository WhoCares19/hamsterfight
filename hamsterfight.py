import sys
import os
import random
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QStackedWidget, QSlider
from PyQt5.QtCore import QTimer, Qt, QTime, QUrl, QRect
from PyQt5.QtGui import QPixmap, QTransform, QPainter
from PyQt5.QtMultimedia import QMediaPlayer, QMediaPlaylist, QMediaContent

# ----------------- Global Config -----------------
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 400
HAMSTER_SIZE = 160
PROJECTILE_SPEED = 10
PLAYER_HEALTH = 100
HAMSTER_BOTTOM_OFFSET = 100
PLAYER_X_OFFSET = 50
ENEMY_X_OFFSET = 50
ENEMY_SHOOT_COOLDOWN = 2000
ARROW_SIZE = 40
IDLE_FRAME_INTERVAL = 150
WIN_FRAME_INTERVAL = 80
SLEEP_FRAME_INTERVAL = 150

# UI Config
GAME_OVER_Y = 20  
CURRENT_VOLUME = 50 

# ----------------- Hamster Data -----------------
# *_source_w/h: Defines the size of the cut from the sheet.
# The code will AUTOMATICALLY resize this cut to 160x160 for display.
HAMSTERS = {
    "Bob": {
        "spritesheet": "Bob/bob_idle.png",
        "projectile": "Projectiles/BobCakeSlice.png",
        "win": "Bob/bob_win.png",
        "sleep": "Bob/bob_sleep.png",
        "win_count": 24,
        "sleep_count": 8,
        # Default source is 160x160 if not specified
    },
    "Dracula": {
        "spritesheet": "Dracula/dracula_idle.png",
        "projectile": "Projectiles/DracTeeth.png",
        "win": "Dracula/dracula_win.png",
        "sleep": "Dracula/dracula_sleep.png",
        "win_count": 24,
        "sleep_count": 8
    },
    "TheHamster": {
        "spritesheet": "TheHamster/thehamster_idle.png",
        "projectile": "Projectiles/TheHamsterBag.png",
        "win": "TheHamster/thehamster_win.png",
        "sleep": "TheHamster/thehamster_sleep.png",
        "win_count": 24,
        "sleep_count": 8
    },
    "McUncle": {
        "spritesheet": "Mcuncle/mcuncle_Idle.png",
        "projectile": "Projectiles/Mcunle_whip.png",
        "win": "Mcuncle/mcuncle_win.png",
        "sleep": "Mcuncle/mcuncle_sleep.png",
        "win_count": 6,
        "sleep_count": 24,
        # Source dimensions updated
        "idle_source_w": 160, "idle_source_h": 160,
        "win_source_w": 180,  "win_source_h": 197,
        "sleep_source_w": 234,"sleep_source_h": 192,
        # Offsets
        "bottom_offset": 110,       # Idle offset
        "win_bottom_offset": 113,  # Specific offset for winning
        "sleep_bottom_offset": 113  # Specific offset for sleeping
    },
    "Dancer": {
        "spritesheet": "Dancer/idle_sprite.png",
        "projectile": "Projectiles/DancerBell.png",
        "win": "Dancer/win_loop.png",
        "sleep": "Dancer/go_sleep.png",
        "win_count": 24, # Reduced from 26 to fix the glitchy last frame
        "sleep_count": 24,
        "idle_source_w": 160, "idle_source_h": 160,
        "win_source_w": 160, "win_source_h": 160,
        "sleep_source_w": 215,"sleep_source_h": 160,
        "keep_aspect": True,  # Prevents distortion for Dancer
        
        # Offsets
        "bottom_offset": 100,       # Idle offset
        "win_bottom_offset": 113,  # Specific offset for winning
        "sleep_bottom_offset": 113  # Specific offset for sleeping
    }
}

# ----------------- Arrow Keys Mapping -----------------
ARROWS = {
    "up": Qt.Key_Up,
    "down": Qt.Key_Down,
    "left": Qt.Key_Left,
    "right": Qt.Key_Right
}

# ----------------- Projectile Class -----------------
class Projectile(QLabel):
    def __init__(self, pixmap_path, parent, start_x, start_y, direction, flip=False):
        super().__init__(parent)
        self.direction = direction
        if not os.path.exists(pixmap_path):
            self.pixmap_orig = QPixmap(32,32)
            self.pixmap_orig.fill(Qt.red)
        else:
            self.pixmap_orig = QPixmap(pixmap_path).scaled(32,32)
            if flip:
                self.pixmap_orig = self.pixmap_orig.transformed(QTransform().scale(-1,1))
        self.setPixmap(self.pixmap_orig)
        self.setGeometry(start_x, start_y, 32, 32)
        self.show()

    def move_projectile(self):
        try:
            self.move(self.x() + PROJECTILE_SPEED * self.direction, self.y())
        except RuntimeError:
            pass

# ----------------- Hamster Class -----------------
class Hamster(QLabel):
    def __init__(self, name, parent, x, y, flip=False):
        super().__init__(parent)
        self.name = name
        
        # Always force the widget size to 160x160
        self.setFixedSize(HAMSTER_SIZE, HAMSTER_SIZE)
        self.setGeometry(x, y, HAMSTER_SIZE, HAMSTER_SIZE)
        
        self.health = PLAYER_HEALTH
        self.frame = 0
        self.frames_count = 6
        self.flip_idle = flip 
        
        # --- LOAD DATA ---
        data = HAMSTERS[name]
        self.idle_src_w = data.get("idle_source_w", HAMSTER_SIZE)
        self.idle_src_h = data.get("idle_source_h", HAMSTER_SIZE)
        self.win_src_w  = data.get("win_source_w", HAMSTER_SIZE)
        self.win_src_h  = data.get("win_source_h", HAMSTER_SIZE)
        self.sleep_src_w = data.get("sleep_source_w", HAMSTER_SIZE)
        self.sleep_src_h = data.get("sleep_source_h", HAMSTER_SIZE)
        
        # --- SCALING MODE ---
        self.keep_aspect = data.get("keep_aspect", False)
        if self.keep_aspect:
            self.setScaledContents(False)
            self.setAlignment(Qt.AlignCenter)
        else:
            self.setScaledContents(True)

        # --- OFFSETS ---
        # Get base offsets. If specific ones aren't defined, fall back to the main offset, then global default.
        self.idle_offset = data.get("bottom_offset", HAMSTER_BOTTOM_OFFSET)
        self.win_offset = data.get("win_bottom_offset", self.idle_offset)
        self.sleep_offset = data.get("sleep_bottom_offset", self.idle_offset)

        self.anim_timer = None
        self.idle_timer = QTimer()
        self.idle_timer.timeout.connect(self.update_frame)
        self.idle_timer.start(IDLE_FRAME_INTERVAL)

        path = data["spritesheet"]
        if not os.path.exists(path):
            self.spritesheet = QPixmap(HAMSTER_SIZE*6, HAMSTER_SIZE)
            self.spritesheet.fill(Qt.red)
        else:
            self.spritesheet = QPixmap(path)
        
        if self.spritesheet.isNull():
            self.spritesheet = QPixmap(HAMSTER_SIZE*6, HAMSTER_SIZE)
            self.spritesheet.fill(Qt.red)

        self.update_frame() 
        self.show()

        self.projectile_path = data["projectile"]
        self.win_sprite = data["win"]
        self.sleep_sprite = data["sleep"]
        self.win_count = data.get("win_count",24)
        self.sleep_count = data.get("sleep_count",8)

        self.custom_anim_index = 0

    def update_frame(self):
        try:
            # Cut from source dimensions
            fw = self.idle_src_w
            fh = self.idle_src_h
            
            idx = self.frame % self.frames_count
            
            # Copy correct chunk
            pix = self.spritesheet.copy(idx * fw, 0, fw, fh)
            
            # Auto-Resize to 160x160
            mode = Qt.KeepAspectRatio if self.keep_aspect else Qt.IgnoreAspectRatio
            pix = pix.scaled(HAMSTER_SIZE, HAMSTER_SIZE, mode, Qt.SmoothTransformation)
            
            if self.flip_idle:
                pix = pix.transformed(QTransform().scale(-1, 1))

            self.setPixmap(pix)
            self.frame = (self.frame + 1) % self.frames_count
        except RuntimeError:
            if self.idle_timer:
                self.idle_timer.stop()
        except Exception:
            pass

    def stop_idle(self):
        if self.idle_timer and self.idle_timer.isActive():
            self.idle_timer.stop()

    def play_custom_animation(self, sprite_path, frame_count, interval_ms, src_w, src_h, flip=False, loop=True):
        if self.anim_timer and self.anim_timer.isActive():
            self.anim_timer.stop()
        
        if not os.path.exists(sprite_path):
            sheet = QPixmap(frame_count*HAMSTER_SIZE, HAMSTER_SIZE)
            sheet.fill(Qt.red)
        else:
            sheet = QPixmap(sprite_path)
            if sheet.isNull():
                 sheet = QPixmap(frame_count*HAMSTER_SIZE, HAMSTER_SIZE)
                 sheet.fill(Qt.red)
        
        self.custom_sheet = sheet
        self.custom_frame_count = frame_count
        self.custom_loop = loop
        self.custom_anim_index = 0
        self.custom_flip = flip
        
        # Store dimensions for this specific animation
        self.current_anim_src_w = src_w
        self.current_anim_src_h = src_h

        def step():
            try:
                idx = self.custom_anim_index % self.custom_frame_count
                
                # Cut using SOURCE dimensions
                frame_pix = self.custom_sheet.copy(
                    idx * self.current_anim_src_w, 
                    0, 
                    self.current_anim_src_w, 
                    self.current_anim_src_h
                )
                
                # Auto-Resize to 160x160
                mode = Qt.KeepAspectRatio if self.keep_aspect else Qt.IgnoreAspectRatio
                frame_pix = frame_pix.scaled(
                    HAMSTER_SIZE, HAMSTER_SIZE, 
                    mode, 
                    Qt.SmoothTransformation
                )
                
                if self.custom_flip:
                    frame_pix = frame_pix.transformed(QTransform().scale(-1, 1))
                
                self.setPixmap(frame_pix)
                self.custom_anim_index += 1
                
                if not self.custom_loop and self.custom_anim_index >= self.custom_frame_count:
                    if self.anim_timer and self.anim_timer.isActive():
                        self.anim_timer.stop()
            except RuntimeError:
                if self.anim_timer:
                    self.anim_timer.stop()
            except Exception:
                pass

        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(step)
        step()
        self.anim_timer.start(interval_ms)

    def set_win(self, flip=False):
        self.stop_idle()
        
        # Reposition for Win state
        new_y = WINDOW_HEIGHT - HAMSTER_SIZE - self.win_offset
        self.move(self.x(), new_y)
        
        self.play_custom_animation(
            self.win_sprite, 
            self.win_count, 
            WIN_FRAME_INTERVAL, 
            self.win_src_w, self.win_src_h,
            flip=flip, 
            loop=True
        )

    def set_sleep(self, flip=False):
        self.stop_idle()
        
        # Reposition for Sleep state
        new_y = WINDOW_HEIGHT - HAMSTER_SIZE - self.sleep_offset
        self.move(self.x(), new_y)
        
        self.play_custom_animation(
            self.sleep_sprite, 
            self.sleep_count, 
            SLEEP_FRAME_INTERVAL, 
            self.sleep_src_w, self.sleep_src_h,
            flip=flip, 
            loop=True
        )

    def stop_all_animations(self):
        if self.anim_timer and self.anim_timer.isActive():
            self.anim_timer.stop()
        if self.idle_timer and self.idle_timer.isActive():
            self.idle_timer.stop()

# ----------------- Volume Mixer Class -----------------
class VolumeMixer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 160) 
        self.setFocusPolicy(Qt.NoFocus) 
        
        self.icon_size = 50
        
        # Audio Setup
        self.player = QMediaPlayer()
        self.playlist = QMediaPlaylist()
        song_path = os.path.abspath(os.path.join("songs", "song1.mp3"))
        if os.path.exists(song_path):
            self.playlist.addMedia(QMediaContent(QUrl.fromLocalFile(song_path)))
            self.playlist.setPlaybackMode(QMediaPlaylist.Loop)
            self.player.setPlaylist(self.playlist)
            self.player.setVolume(CURRENT_VOLUME)
            self.player.play()
        
        # Sprite Setup
        self.frames = []
        sprite_path = os.path.join("songs", "volumemixer.png")
        if os.path.exists(sprite_path):
            sheet = QPixmap(sprite_path)
            if not sheet.isNull():
                for i in range(16):
                    pix = sheet.copy(i*195, 0, 195, 195)
                    pix = pix.scaled(self.icon_size, self.icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.frames.append(pix)
        
        if not self.frames:
            fill = QPixmap(self.icon_size, self.icon_size)
            fill.fill(Qt.blue)
            self.frames = [fill]

        self.current_frame = 0
        self.is_muted = False

        # Visuals
        self.slider = QSlider(Qt.Vertical, self)
        self.slider.setGeometry(15, 0, 30, 100) 
        self.slider.setRange(0, 100)
        self.slider.setValue(CURRENT_VOLUME)
        self.slider.hide()
        self.slider.setFocusPolicy(Qt.NoFocus)
        self.slider.valueChanged.connect(self.on_volume_change)

        self.icon_lbl = QLabel(self)
        self.icon_lbl.setGeometry(5, 110, self.icon_size, self.icon_size)
        self.icon_lbl.setPixmap(self.frames[0])

        # Timers
        self.base_anim_interval = 100
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.update_anim)
        self.anim_timer.start(self.base_anim_interval)

        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self.slider.hide)
        
        self.update_anim_speed()

    def on_volume_change(self, val):
        global CURRENT_VOLUME
        CURRENT_VOLUME = val 
        
        if self.is_muted:
            self.is_muted = False
            self.player.setMuted(False)
            self.anim_timer.start()
        
        self.player.setVolume(val)
        self.update_anim_speed()

    def update_anim_speed(self):
        val = self.slider.value()
        if val < 50:
            interval = int(self.base_anim_interval * 1.5)
        else:
            interval = self.base_anim_interval
        self.anim_timer.setInterval(interval)

    def update_anim(self):
        try:
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.icon_lbl.setPixmap(self.frames[self.current_frame])
        except RuntimeError:
            self.anim_timer.stop()

    def mousePressEvent(self, event):
        if self.icon_lbl.geometry().contains(event.pos()):
            self.toggle_mute()

    def toggle_mute(self):
        self.is_muted = not self.is_muted
        if self.is_muted:
            self.player.setMuted(True)
            self.anim_timer.stop()
            self.icon_lbl.setPixmap(self.frames[0])
        else:
            self.player.setMuted(False)
            self.anim_timer.start()

    def enterEvent(self, event):
        self.hide_timer.stop()
        self.slider.show()

    def leaveEvent(self, event):
        self.hide_timer.start(2000)

    def cleanup(self):
        try:
            self.player.stop()
            self.anim_timer.stop()
            self.hide_timer.stop()
        except Exception:
            pass

# ----------------- Game Widget -----------------
class Game(QWidget):
    def __init__(self, player_name):
        super().__init__()
        self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self.setFocusPolicy(Qt.StrongFocus)
        self.game_ended = False

        # Background
        bg_folder = "backgrounds"
        if not os.path.exists(bg_folder):
            self.background = QPixmap(WINDOW_WIDTH,WINDOW_HEIGHT)
            self.background.fill(Qt.black)
        else:
            bg_files = [f for f in os.listdir(bg_folder) if f.lower().endswith((".png",".jpg",".jpeg"))]
            if not bg_files:
                self.background = QPixmap(WINDOW_WIDTH,WINDOW_HEIGHT)
                self.background.fill(Qt.black)
            else:
                bg_path = os.path.join(bg_folder, random.choice(bg_files))
                self.background = QPixmap(bg_path).scaled(WINDOW_WIDTH,WINDOW_HEIGHT)

        # Hamster positions
        # Calculate Y for Player based on specific offset
        p_data = HAMSTERS[player_name]
        p_offset = p_data.get("bottom_offset", HAMSTER_BOTTOM_OFFSET)
        p_y = WINDOW_HEIGHT - HAMSTER_SIZE - p_offset
        self.player = Hamster(player_name, self, PLAYER_X_OFFSET, p_y)

        # Calculate Y for Enemy based on specific offset
        enemy_name = random.choice([h for h in HAMSTERS.keys() if h != player_name])
        e_data = HAMSTERS[enemy_name]
        e_offset = e_data.get("bottom_offset", HAMSTER_BOTTOM_OFFSET)
        e_y = WINDOW_HEIGHT - HAMSTER_SIZE - e_offset
        self.enemy = Hamster(enemy_name, self, WINDOW_WIDTH - HAMSTER_SIZE - ENEMY_X_OFFSET, e_y, flip=True)

        self.projectiles = []
        self.enemy_projectiles = []

        self.last_enemy_shoot = QTime.currentTime().addMSecs(-ENEMY_SHOOT_COOLDOWN)

        self.game_timer = QTimer()
        self.game_timer.timeout.connect(self.game_loop)
        self.game_timer.start(30)

        self.health_label = QLabel(self)
        self.health_label.setGeometry(10,10,250,30)
        self.update_health()

        # Arrows
        self.current_arrow_label = None
        self.current_arrow = None
        self.show_new_arrow()

        # --- End Game UI Elements ---
        
        # 1. Main End Message
        self.end_label = QLabel(self)
        self.end_label.setAlignment(Qt.AlignCenter)
        self.end_label.hide()

        # 2. Restart Button
        self.restart_button = QPushButton("Restart", self)
        self.restart_button.hide()
        self.restart_button.clicked.connect(self.restart_game)

        # 3. Middle Text
        self.middle_text = QLabel("or would you like to", self)
        self.middle_text.setAlignment(Qt.AlignCenter)
        self.middle_text.hide()
        self.middle_text.setStyleSheet("color: white; font-weight: bold;") 

        # 4. Back Button
        self.menu_button = QPushButton("Back to Selection", self)
        self.menu_button.hide()
        self.menu_button.clicked.connect(self.back_to_menu)

        # Volume Mixer
        mixer_x = WINDOW_WIDTH - 60 - 20
        mixer_y = WINDOW_HEIGHT - 160 - 20 
        
        self.volume_mixer = VolumeMixer(self)
        self.volume_mixer.move(mixer_x, mixer_y)
        self.volume_mixer.show()

    def showEvent(self, event):
        self.setFocus()
        super().showEvent(event)

    def mousePressEvent(self, event):
        self.setFocus()
        super().mousePressEvent(event)

    def paintEvent(self,event):
        painter = QPainter(self)
        painter.drawPixmap(0,0,self.background)

    def keyPressEvent(self,event):
        if self.game_ended: return
        if self.current_arrow is None: return
        required_key = ARROWS[self.current_arrow]
        if event.key() == required_key:
            self.shoot_player()
            self.show_new_arrow()

    def shoot_player(self):
        if self.game_ended: return
        direction = 1
        proj = Projectile(self.player.projectile_path,self,
                          self.player.x()+HAMSTER_SIZE,
                          self.player.y()+HAMSTER_SIZE//2-16,
                          direction)
        self.projectiles.append(proj)

    def show_new_arrow(self):
        if self.game_ended: return
        if self.current_arrow_label:
            try:
                self.current_arrow_label.deleteLater()
            except Exception:
                pass
            self.current_arrow_label = None
        self.current_arrow = random.choice(list(ARROWS.keys()))
        arrow_path = f"arrows/{self.current_arrow}.png"
        if os.path.exists(arrow_path):
            pix = QPixmap(arrow_path).scaled(ARROW_SIZE,ARROW_SIZE)
        else:
            pix = QPixmap(ARROW_SIZE,ARROW_SIZE)
            pix.fill(Qt.red)
        label = QLabel(self)
        label.setPixmap(pix)
        label.setGeometry(self.player.x()+HAMSTER_SIZE//2-ARROW_SIZE//2,
                          self.player.y()-ARROW_SIZE-10,
                          ARROW_SIZE,ARROW_SIZE)
        label.show()
        self.current_arrow_label = label

    def enemy_shoot(self):
        if self.game_ended: return
        now = QTime.currentTime()
        if self.last_enemy_shoot.msecsTo(now) < ENEMY_SHOOT_COOLDOWN:
            return
        self.last_enemy_shoot = now
        proj = Projectile(self.enemy.projectile_path,self,
                          self.enemy.x()-32,
                          self.enemy.y()+HAMSTER_SIZE//2-16,
                          -1, flip=True)
        self.enemy_projectiles.append(proj)

    def game_loop(self):
        if self.game_ended: return

        # Player projectiles
        for proj in self.projectiles[:]:
            proj.move_projectile()
            if proj.x() > WINDOW_WIDTH:
                proj.deleteLater()
                self.projectiles.remove(proj)
                continue
            if self.pixel_collision(proj, self.enemy):
                self.enemy.health -= 10
                try:
                    proj.deleteLater()
                except Exception:
                    pass
                if proj in self.projectiles:
                    self.projectiles.remove(proj)
                self.update_health()
                if self.enemy.health <= 0:
                    self.end_game(winner="player")
                continue

        # Enemy projectiles + enemy shooting
        self.enemy_shoot()
        for proj in self.enemy_projectiles[:]:
            proj.move_projectile()
            if proj.x() < -32:
                proj.deleteLater()
                self.enemy_projectiles.remove(proj)
                continue
            if self.pixel_collision(proj, self.player):
                self.player.health -= 10
                try:
                    proj.deleteLater()
                except Exception:
                    pass
                if proj in self.enemy_projectiles:
                    self.enemy_projectiles.remove(proj)
                self.update_health()
                if self.player.health <= 0:
                    self.end_game(winner="enemy")
                continue

    def pixel_collision(self, proj, hamster):
        try:
            proj_img = proj.pixmap().toImage()
            hamster_img = hamster.pixmap().toImage()
        except Exception:
            return False
        rect1 = proj.geometry()
        rect2 = hamster.geometry()
        overlap = rect1.intersected(rect2)
        if overlap.isNull():
            return False
        ow = overlap.width()
        oh = overlap.height()
        for x in range(ow):
            for y in range(oh):
                px = overlap.x() - rect1.x() + x
                py = overlap.y() - rect1.y() + y
                hx = overlap.x() - rect2.x() + x
                hy = overlap.y() - rect2.y() + y
                if px < 0 or py < 0 or hx < 0 or hy < 0:
                    continue
                if px >= proj_img.width() or py >= proj_img.height(): continue
                if hx >= hamster_img.width() or hy >= hamster_img.height(): continue
                if proj_img.pixelColor(px,py).alpha() > 0 and hamster_img.pixelColor(hx,hy).alpha() > 0:
                    return True
        return False

    def update_health(self):
        self.health_label.setText(f"Player: {self.player.health}  Enemy: {self.enemy.health}")

    def end_game(self, winner):
        if self.game_ended: return
        self.game_ended = True

        try:
            if self.game_timer.isActive():
                self.game_timer.stop()
        except Exception:
            pass

        self.player.stop_all_animations()
        self.enemy.stop_all_animations()

        if self.current_arrow_label:
            self.current_arrow_label.deleteLater()
            self.current_arrow_label = None

        for proj in self.projectiles+self.enemy_projectiles:
            try:
                proj.deleteLater()
            except Exception:
                pass
        self.projectiles.clear()
        self.enemy_projectiles.clear()

        if winner == "player":
            self.player.set_win(flip=False)
            self.enemy.set_sleep(flip=True)
            message = "Congratulations hamster, you won the round!"
        else:
            self.enemy.set_win(flip=True)
            self.player.set_sleep(flip=False)
            message = "Oh no! The enemy won the round."

        # Configure UI positions
        start_y = GAME_OVER_Y
        
        # 1. Message
        self.end_label.setText(message)
        self.end_label.setGeometry(0, start_y, WINDOW_WIDTH, 40) 
        self.end_label.show()

        # Row 2 Y position
        button_y = start_y + 50
        
        # Restart Button
        self.restart_button.setGeometry(100, button_y, 100, 40)
        self.restart_button.show()
        
        # Middle Text
        self.middle_text.setGeometry(210, button_y, 130, 40)
        self.middle_text.show()
        
        # Back Button
        self.menu_button.setGeometry(350, button_y, 130, 40)
        self.menu_button.show()

    def cleanup_before_exit(self):
        self.volume_mixer.cleanup()
        self.player.stop_all_animations()
        self.enemy.stop_all_animations()
        if self.game_timer.isActive():
            self.game_timer.stop()

    def restart_game(self):
        self.cleanup_before_exit()
        
        parent_stack = self.parentWidget()
        new_game = Game(self.player.name)
        parent_stack.addWidget(new_game)
        parent_stack.setCurrentWidget(new_game)
        
        try:
            parent_stack.removeWidget(self)
            self.deleteLater()
        except Exception:
            pass

    def back_to_menu(self):
        self.cleanup_before_exit()
        parent_stack = self.parentWidget()
        parent_stack.setCurrentIndex(0)
        
        try:
            parent_stack.removeWidget(self)
            self.deleteLater()
        except Exception:
            pass

# ----------------- Selection Screen -----------------
class SelectionScreen(QWidget):
    def __init__(self, stack):
        super().__init__()
        self.stack = stack
        self.setFixedSize(WINDOW_WIDTH,WINDOW_HEIGHT)
        y = 50
        for name in HAMSTERS.keys():
            btn = QPushButton(name,self)
            btn.setGeometry(WINDOW_WIDTH//2-50,y,100,40)
            btn.clicked.connect(lambda checked,n=name:self.select_hamster(n))
            y += 60

    def select_hamster(self,name):
        game = Game(name)
        self.stack.addWidget(game)
        self.stack.setCurrentWidget(game)

# ----------------- Main -----------------
class MainWindow(QStackedWidget):
    def __init__(self):
        super().__init__()
        self.selection_screen = SelectionScreen(self)
        self.addWidget(self.selection_screen)
        self.setFixedSize(WINDOW_WIDTH,WINDOW_HEIGHT)
        self.show()

if __name__=="__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())
