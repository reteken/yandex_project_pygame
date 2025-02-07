import pygame
from pygame.locals import *
import sys
import random
import time
import cv2
import numpy as np
import json
from network import NetworkClient  # импортируем наш модуль сетевого клиента

pygame.init()
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GREEN = (0, 250, 0)
GRAY = (128, 128, 128)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Dmitriy Combat 2D")
clock = pygame.time.Clock()


def get_frame_surface(cap, w, h):
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
        if not ret:
            return None
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    frame = cv2.resize(frame, (w, h))
    return pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))


class Button:
    def __init__(
        self,
        rect,
        color,
        text,
        text_color=WHITE,
        border_color=GRAY,
        no_background=False,
    ):
        self.rect = rect
        self.color = color
        self.text = text
        self.text_color = text_color
        self.border_color = border_color
        self.font = pygame.font.SysFont(None, 36)
        self.no_background = no_background

    def draw(self, surface):
        if not self.no_background:
            pygame.draw.rect(
                surface, self.border_color, self.rect.inflate(10, 10), border_radius=10
            )
            pygame.draw.rect(surface, self.color, self.rect, border_radius=10)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, owner, animation_frames, bullet_type):
        super().__init__()
        self.animation_frames = animation_frames
        self.current_frame = 0
        self.bullet_type = bullet_type
        if direction < 0:
            self.animation_frames = [
                pygame.transform.flip(f, True, False) for f in self.animation_frames
            ]
        self.image = self.animation_frames[self.current_frame]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x + random.randint(10, 50), y + random.randint(-10, 10))
        self.speed = 10 * direction
        self.owner = owner
        self.animation_speed = 1
        self.frame_counter = 0

    def update(self):
        self.rect.x += self.speed
        if self.rect.right < 0 or self.rect.left > SCREEN_WIDTH:
            self.kill()
        self.frame_counter += self.animation_speed
        if self.frame_counter >= 1:
            self.current_frame = (self.current_frame + 1) % len(self.animation_frames)
            self.image = self.animation_frames[self.current_frame]
            self.frame_counter = 0


class Player(pygame.sprite.Sprite):
    def __init__(
        self, x, y, run_frames, jump_frames, hit_frames, idle_frames, is_pepe=False
    ):
        super().__init__()
        self.is_pepe = is_pepe
        self.animation_frames = run_frames
        self.jump_frames = jump_frames
        self.hit_frames = hit_frames
        self.idle_frames = idle_frames
        self.idle_frame = 0
        self.current_frame = 0
        self.jump_frame = 0
        self.hit_frame = 0
        self.animation_speed = 1.1
        self.frame_counter = 0
        self.image = self.animation_frames[self.current_frame]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.mask = pygame.mask.from_surface(self.image)
        self.health = 100
        self.speed = 10
        self.jump_speed = -15
        self.gravity = 0.8
        self.dy = 0
        self.on_ground = False
        self.is_moving = False
        self.is_jumping = False
        self.is_hitting = False
        self.facing_right = True
        self.last_shot_time = 0
        self.last_hit_time = 0

    def animate(self):
        if self.is_jumping:
            self.jump_frame += self.animation_speed
            if self.jump_frame >= len(self.jump_frames):
                self.jump_frame = len(self.jump_frames) - 1
            self.image = self.jump_frames[int(self.jump_frame)]
        elif self.is_hitting:
            self.hit_frame += self.animation_speed
            if self.hit_frame >= len(self.hit_frames):
                self.hit_frame = 0
                self.is_hitting = False
            self.image = self.hit_frames[int(self.hit_frame)]
        elif self.is_moving:
            self.frame_counter += self.animation_speed
            if self.frame_counter >= 1:
                self.current_frame = (self.current_frame + 1) % len(
                    self.animation_frames
                )
                self.image = self.animation_frames[self.current_frame]
                self.frame_counter = 0
        else:
            self.idle_frame += self.animation_speed
            if self.idle_frame >= len(self.idle_frames):
                self.idle_frame = 0
            self.image = self.idle_frames[int(self.idle_frame)]
        self.mask = pygame.mask.from_surface(self.image)

    def inputer(
        self, other, keys, controls, bullets_group, bullet_animation_frames, bullet_type
    ):
        self.is_moving = False
        if keys[controls["left"]] and self.rect.x > 0:
            self.rect.x -= self.speed
            self.is_moving = True
            if self.facing_right:
                self.facing_right = False
                self.flip_images()
        if keys[controls["right"]] and self.rect.x + 50 < SCREEN_WIDTH:
            self.rect.x += self.speed
            self.is_moving = True
            if not self.facing_right:
                self.facing_right = True
                self.flip_images()
        if keys[controls["jump"]] and self.on_ground:
            self.dy = self.jump_speed
            self.on_ground = False
            self.is_jumping = True
        current_time = time.time()
        if keys[controls["shoot"]] and current_time - self.last_shot_time > 0.1:
            self.last_shot_time = current_time
            direction = 1 if self.rect.x < other.rect.x else -1
            for i in range(3):
                bullet = Bullet(
                    self.rect.centerx,
                    self.rect.centery - 10 + i * 10,
                    direction,
                    self,
                    bullet_animation_frames,
                    bullet_type,
                )
                bullets_group.add(bullet)
        if keys[controls["hit"]] and current_time - self.last_hit_time > 0.5:
            self.is_hitting = True
            self.hit_frame = 0
            self.last_hit_time = current_time
            if self.facing_right:
                self.rect.x += 10
            else:
                self.rect.x -= 10
            if self.rect.colliderect(other.rect):
                other.health -= 15

    def flip_images(self):
        self.animation_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.animation_frames
        ]
        self.jump_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.jump_frames
        ]
        self.hit_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.hit_frames
        ]
        self.idle_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.idle_frames
        ]
        self.image = self.animation_frames[self.current_frame]
        self.mask = pygame.mask.from_surface(self.image)

    def gravity_helper(self):
        self.dy += self.gravity
        self.rect.y += self.dy
        floor_level = SCREEN_HEIGHT - 100
        if self.rect.bottom >= floor_level:
            self.rect.bottom = floor_level
            self.dy = 0
            self.on_ground = True
            self.is_jumping = False
            self.jump_frame = 0

    def update(
        self, other, keys, controls, bullets_group, bullet_animation_frames, bullet_type
    ):
        self.inputer(
            other, keys, controls, bullets_group, bullet_animation_frames, bullet_type
        )
        self.animate()
        self.gravity_helper()

    def draw_health_bar(self, screen, x, y):
        pygame.draw.rect(screen, RED, (x, y, 100, 10))
        pygame.draw.rect(screen, GREEN, (x, y, self.health, 10))


class AIPlayer(Player):
    def inputer(
        self, other, keys, controls, bullets_group, bullet_animation_frames, bullet_type
    ):
        pass


def load_image_with_fallback(path, width, height, fallback_color):
    try:
        image = pygame.image.load(path).convert_alpha()
    except:
        image = pygame.Surface((width, height))
        image.fill(fallback_color)
    return pygame.transform.scale(image, (width, height))


def load_animation(folder, frame_count, prefix, width=350, height=350):
    frames = []
    for i in range(frame_count):
        path = f"{folder}/{prefix}_{i+1}.png"
        frame_surf = load_image_with_fallback(path, width, height, ORANGE)
        frames.append(frame_surf)
    return frames


def create_pepe_animation(folder, frame_count, prefix, width=300, height=300):
    frames = []
    for i in range(frame_count):
        frame_number = str(i).zfill(5)
        path = f"{folder}/{prefix}_{frame_number}.png"
        frame_surf = load_image_with_fallback(path, width, height, BLUE)
        frames.append(frame_surf)
    return frames


def load_bullet_animation(folder, frame_count, prefix, width=60, height=60, color=GRAY):
    frames = []
    for i in range(frame_count):
        frame_number = str(i).zfill(5)
        path = f"{folder}/{prefix}_{frame_number}.png"
        frame_surf = load_image_with_fallback(path, width, height, color)
        frames.append(frame_surf)
    return frames


def show_loading_screen(progress, total):
    screen.fill(BLACK)
    font = pygame.font.SysFont(None, 74)
    loading_text = font.render("Loading...", True, WHITE)
    loading_rect = loading_text.get_rect(
        center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)
    )
    screen.blit(loading_text, loading_rect)
    bar_width = 400
    bar_height = 30
    bar_x = (SCREEN_WIDTH - bar_width) // 2
    bar_y = SCREEN_HEIGHT // 2
    pygame.draw.rect(
        screen, GRAY, (bar_x, bar_y, bar_width, bar_height), border_radius=5
    )
    loaded_width = int(bar_width * (progress / total))
    pygame.draw.rect(
        screen, GREEN, (bar_x, bar_y, loaded_width, bar_height), border_radius=5
    )
    pygame.display.flip()


def load_all_assets():
    total_load_steps = 400
    current_progress = 0
    show_loading_screen(current_progress, total_load_steps)
    durov_run = load_animation("durov", 20, "дуров бежит")
    current_progress += 20
    show_loading_screen(current_progress, total_load_steps)
    durov_jump = load_animation("durov_jump", 49, "durov_jump")
    current_progress += 49
    show_loading_screen(current_progress, total_load_steps)
    durov_hit = load_animation("damage_1", 37, "durov_hit")
    current_progress += 37
    show_loading_screen(current_progress, total_load_steps)
    durov_idle = create_pepe_animation("waiter_durov", 55, "стойкаааааааааааа")
    current_progress += 55
    show_loading_screen(current_progress, total_load_steps)
    pepe_run = create_pepe_animation("pepe_run", 31, "бег пепе")
    current_progress += 31
    show_loading_screen(current_progress, total_load_steps)
    pepe_jump = create_pepe_animation("pepe_run", 30, "бег пепе")
    current_progress += 30
    show_loading_screen(current_progress, total_load_steps)
    pepe_hit = create_pepe_animation("hit_pepe_1", 28, "удар пепе 1")
    current_progress += 28
    show_loading_screen(current_progress, total_load_steps)
    pepe_idle = create_pepe_animation("waiter_pepe", 60, "пепе стойка")
    current_progress += 60
    show_loading_screen(current_progress, total_load_steps)
    ton_bullet = load_bullet_animation("ton coin", 155, "ton coin", 45, 45, GRAY)
    current_progress += 155
    show_loading_screen(current_progress, total_load_steps)
    pepe_bullet = load_bullet_animation("pepe coin", 155, "пепе пуля", 45, 45, PURPLE)
    current_progress += 155
    show_loading_screen(current_progress, total_load_steps)
    main_video = cv2.VideoCapture("поле_1.mp4")
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)
    lobby_video = cv2.VideoCapture("лобби.mp4")
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)
    start_button_video = cv2.VideoCapture("start game.mov")
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)
    durov_idle_video = cv2.VideoCapture("дуров стойка галаграмма.mp4")
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)
    pepe_idle_video = cv2.VideoCapture("пепе стойка галограмма.mp4")
    current_progress += 1
    show_loading_screen(current_progress, total_load_steps)
    return {
        "durov": {
            "run": durov_run,
            "jump": durov_jump,
            "hit": durov_hit,
            "idle": durov_idle,
        },
        "pepe": {
            "run": pepe_run,
            "jump": pepe_jump,
            "hit": pepe_hit,
            "idle": pepe_idle,
        },
        "bullets": {
            "ton": ton_bullet,
            "pepe": pepe_bullet,
        },
        "video": main_video,
        "video_lobby": lobby_video,
        "video_start": start_button_video,
        "video_durov_idle": durov_idle_video,
        "video_pepe_idle": pepe_idle_video,
    }


def shop_screen():
    scroll_offset = 0
    squares = []
    square_size = 200
    gap = 50
    base_x = 200
    base_y = 200
    for col in range(2):
        for row in range(2):
            x = base_x + col * (square_size + gap)
            y = base_y + row * (square_size + gap)
            squares.append(pygame.Rect(x, y, square_size, square_size))
    back_button = Button(pygame.Rect(50, SCREEN_HEIGHT - 100, 200, 60), BLUE, "Back")
    running = True
    while running:
        screen.fill(WHITE)
        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_UP:
                    scroll_offset += 50
                if event.key == K_DOWN:
                    scroll_offset -= 50
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                if back_button.is_clicked(pos):
                    running = False
        for sq in squares:
            shifted_rect = sq.move(0, scroll_offset)
            pygame.draw.rect(screen, ORANGE, shifted_rect)
        back_button.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)


def main_game(player1_choice, player2_choice, assets):
    cap = assets["video"]
    shadow_img = pygame.image.load("тень.png").convert_alpha()
    shadow_img = pygame.transform.scale(
        shadow_img, (shadow_img.get_width() // 4, shadow_img.get_height() // 4)
    )
    fixed_shadow_y = SCREEN_HEIGHT - 100 - (shadow_img.get_height() // 2)

    def get_video_frame_surface():
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                return None
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
        return pygame.surfarray.make_surface(np.transpose(frame, (1, 0, 2)))

    player1_controls = {
        "left": K_a,
        "right": K_d,
        "jump": K_w,
        "shoot": K_SPACE,
        "hit": K_e,
    }
    player2_controls = {
        "left": K_LEFT,
        "right": K_RIGHT,
        "jump": K_UP,
        "shoot": K_RCTRL,
        "hit": K_LALT,
    }

    from network import NetworkClient

    net_client = assets.get("net_client")
    if not net_client:
        net_client = NetworkClient("185.125.231.122", 5000)
        assets["net_client"] = net_client

    class AIPlayerLocal(AIPlayer):
        def __init__(
            self, x, y, run_frames, jump_frames, hit_frames, idle_frames, is_pepe=False
        ):
            super().__init__(
                x, y, run_frames, jump_frames, hit_frames, idle_frames, is_pepe=is_pepe
            )
            self.desired_distance = 250
            self.close_range = 180
            self.far_range = 800

        def inputer(
            self,
            other,
            keys,
            controls,
            bullets_group,
            bullet_animation_frames,
            bullet_type,
        ):
            self.is_moving = False
            direction = 1 if other.rect.x > self.rect.x else -1
            distance = abs(self.rect.centerx - other.rect.centerx)
            if distance < self.close_range:
                if random.random() < 0.1:
                    self.rect.x -= self.speed * direction
                    self.is_moving = True
                    if direction == 1 and self.facing_right:
                        self.flip_images()
                        self.facing_right = False
                    elif direction == -1 and not self.facing_right:
                        self.flip_images()
                        self.facing_right = True
                else:
                    self.rect.x += self.speed * direction
                    self.is_moving = True
                    if direction == 1 and not self.facing_right:
                        self.flip_images()
                        self.facing_right = True
                    elif direction == -1 and self.facing_right:
                        self.flip_images()
                        self.facing_right = False
            elif distance > self.far_range:
                self.rect.x += self.speed * direction
                self.is_moving = True
                if direction == 1 and not self.facing_right:
                    self.flip_images()
                    self.facing_right = True
                elif direction == -1 and self.facing_right:
                    self.flip_images()
                    self.facing_right = False
            else:
                if random.random() < 0.02:
                    step_dir = 1 if random.random() < 0.5 else -1
                    self.rect.x += step_dir * self.speed
                    self.is_moving = True
                    if step_dir == 1 and not self.facing_right:
                        self.flip_images()
                        self.facing_right = True
                    elif step_dir == -1 and self.facing_right:
                        self.flip_images()
                        self.facing_right = False
            self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
            if self.on_ground and random.random() < 0.03:
                self.dy = self.jump_speed
                self.on_ground = False
                self.is_jumping = True
            current_time = time.time()
            if current_time - self.last_shot_time > 0.2:
                self.last_shot_time = current_time
                for i in range(3):
                    bullet = Bullet(
                        self.rect.centerx,
                        self.rect.centery - 10 + i * 10,
                        direction,
                        self,
                        bullet_animation_frames,
                        bullet_type,
                    )
                    bullets_group.add(bullet)
            if distance < 110 and current_time - self.last_hit_time > 1.0:
                if random.random() < 0.6:
                    self.is_hitting = True
                    self.hit_frame = 0
                    self.last_hit_time = current_time
                    if direction == 1:
                        self.rect.x += 15
                    else:
                        self.rect.x -= 15
                    if self.rect.colliderect(other.rect):
                        other.health -= 10
            self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
            floor_level = SCREEN_HEIGHT - 100
            if self.rect.bottom >= floor_level:
                self.rect.bottom = floor_level
                self.dy = 0
                self.on_ground = True
                self.is_jumping = False
                self.jump_frame = 0

    if player1_choice == "durov":
        p1_run_frames = assets["durov"]["run"]
        p1_jump_frames = assets["durov"]["jump"]
        p1_hit_frames = assets["durov"]["hit"]
        p1_idle_frames = assets["durov"]["idle"]
        p1_is_pepe = False
    elif player1_choice == "pepe":
        p1_run_frames = assets["pepe"]["run"]
        p1_jump_frames = assets["pepe"]["jump"]
        p1_hit_frames = assets["pepe"]["hit"]
        p1_idle_frames = assets["pepe"]["idle"]
        p1_is_pepe = True
    else:
        p1_run_frames = assets["durov"]["run"]
        p1_jump_frames = assets["durov"]["jump"]
        p1_hit_frames = assets["durov"]["hit"]
        p1_idle_frames = assets["durov"]["idle"]
        p1_is_pepe = False

    if player2_choice == "durov":
        p2_run_frames = assets["durov"]["run"]
        p2_jump_frames = assets["durov"]["jump"]
        p2_hit_frames = assets["durov"]["hit"]
        p2_idle_frames = assets["durov"]["idle"]
        p2_is_pepe = False
    elif player2_choice == "pepe":
        p2_run_frames = assets["pepe"]["run"]
        p2_jump_frames = assets["pepe"]["jump"]
        p2_hit_frames = assets["pepe"]["hit"]
        p2_idle_frames = assets["pepe"]["idle"]
        p2_is_pepe = True
    else:
        p2_run_frames = assets["durov"]["run"]
        p2_jump_frames = assets["durov"]["jump"]
        p2_hit_frames = assets["durov"]["hit"]
        p2_idle_frames = assets["durov"]["idle"]
        p2_is_pepe = False

    p1_bullet_frames = (
        assets["bullets"]["pepe"] if p1_is_pepe else assets["bullets"]["ton"]
    )
    p2_bullet_frames = (
        assets["bullets"]["pepe"] if p2_is_pepe else assets["bullets"]["ton"]
    )
    p1_bullet_type = "pepe" if p1_is_pepe else "ton"
    p2_bullet_type = "pepe" if p2_is_pepe else "ton"

    if player1_choice == "ai":
        player1 = AIPlayerLocal(
            100,
            SCREEN_HEIGHT - 250,
            p1_run_frames,
            p1_jump_frames,
            p1_hit_frames,
            p1_idle_frames,
            is_pepe=p1_is_pepe,
        )
    else:
        player1 = Player(
            100,
            SCREEN_HEIGHT - 250,
            p1_run_frames,
            p1_jump_frames,
            p1_hit_frames,
            p1_idle_frames,
            is_pepe=p1_is_pepe,
        )

    if player2_choice == "ai":
        player2 = AIPlayerLocal(
            SCREEN_WIDTH - 200,
            SCREEN_HEIGHT - 250,
            p2_run_frames,
            p2_jump_frames,
            p2_hit_frames,
            p2_idle_frames,
            is_pepe=p2_is_pepe,
        )
    else:
        player2 = Player(
            SCREEN_WIDTH - 200,
            SCREEN_HEIGHT - 250,
            p2_run_frames,
            p2_jump_frames,
            p2_hit_frames,
            p2_idle_frames,
            is_pepe=p2_is_pepe,
        )

    all_sprites = pygame.sprite.Group()
    all_sprites.add(player1, player2)
    bullets = pygame.sprite.Group()

    def show_winner_screen(winner_text):
        font = pygame.font.SysFont(None, 74)
        text_surf = font.render(winner_text, True, YELLOW)
        text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        screen.blit(text_surf, text_rect)
        pygame.display.flip()
        pygame.time.wait(2000)

    running = True
    winner = None
    round_duration = 60
    start_time = time.time()
    time_font = pygame.font.SysFont(None, 60)

    while running:
        video_surface = get_video_frame_surface()
        if video_surface:
            screen.blit(video_surface, (0, 0))
        else:
            screen.fill(WHITE)

        # Отправляем состояние игрока на сервер (онлайн)
        state = {
            "player_id": "player1",  # Здесь нужно заменить на уникальный идентификатор
            "x": player1.rect.x,
            "y": player1.rect.y,
            "health": player1.health,
            "action": "update",
        }
        net_client.send(state)
        while net_client.received_messages:
            message = net_client.received_messages.pop(0)
            # Обработка сообщений от сервера: обновление состояний других игроков
            print("Received:", message)

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()

        elapsed_time = time.time() - start_time
        remaining_time = round_duration - elapsed_time
        if remaining_time <= 0:
            winner = "DRAW!"
            running = False
        else:
            timer_text = str(int(remaining_time))
            text_surf = time_font.render(timer_text, True, YELLOW)
            text_rect = text_surf.get_rect(center=(SCREEN_WIDTH // 2, 50))
            screen.blit(text_surf, text_rect)

        keys = pygame.key.get_pressed()
        p1_keys = {key: keys[key] for key in player1_controls.values()}
        p2_keys = {key: keys[key] for key in player2_controls.values()}

        player1.update(
            player2,
            p1_keys,
            player1_controls,
            bullets,
            p1_bullet_frames,
            p1_bullet_type,
        )
        player2.update(
            player1,
            p2_keys,
            player2_controls,
            bullets,
            p2_bullet_frames,
            p2_bullet_type,
        )
        bullets.update()

        for bullet in bullets:
            if bullet.owner != player1 and pygame.sprite.collide_mask(bullet, player1):
                player1.health = max(0, player1.health - 1)
                bullet.kill()
            if bullet.owner != player2 and pygame.sprite.collide_mask(bullet, player2):
                player2.health = max(0, player2.health - 1)
                bullet.kill()

        if player1.health <= 0 or player2.health <= 0:
            if player1.health <= 0 < player2.health:
                winner = "Player 2 WINS!"
            elif player2.health <= 0 < player1.health:
                winner = "Player 1 WINS!"
            else:
                winner = "DRAW!"
            running = False

        shadow_x1 = player1.rect.centerx - shadow_img.get_width() // 2
        screen.blit(shadow_img, (shadow_x1, fixed_shadow_y))
        shadow_x2 = player2.rect.centerx - shadow_img.get_width() // 2
        screen.blit(shadow_img, (shadow_x2, fixed_shadow_y))

        all_sprites.draw(screen)
        bullets.draw(screen)

        player1.draw_health_bar(screen, 50, 50)
        player2.draw_health_bar(screen, SCREEN_WIDTH - 150, 50)

        pygame.display.flip()
        clock.tick(FPS)

    if winner is not None:
        show_winner_screen(winner)


def main_menu(assets):
    cap_lobby = assets["video_lobby"]
    cap_start = assets["video_start"]
    cap_durov_idle = assets["video_durov_idle"]
    cap_pepe_idle = assets["video_pepe_idle"]
    font = pygame.font.SysFont(None, 74)

    shop_button = Button(pygame.Rect(20, 20, 150, 50), BLUE, "Shop", border_color=GRAY)
    player1_choice = "durov"
    player2_choice = "durov"

    left_buttons = [
        Button(pygame.Rect(50, 200, 200, 60), BLUE, "Durov", border_color=GRAY),
        Button(pygame.Rect(50, 280, 200, 60), BLUE, "pepe", border_color=GRAY),
        Button(pygame.Rect(50, 360, 200, 60), BLUE, "AI", border_color=GRAY),
    ]
    right_buttons = [
        Button(
            pygame.Rect(SCREEN_WIDTH - 250, 200, 200, 60),
            RED,
            "Durov",
            border_color=GRAY,
        ),
        Button(
            pygame.Rect(SCREEN_WIDTH - 250, 280, 200, 60),
            RED,
            "pepe",
            border_color=GRAY,
        ),
        Button(
            pygame.Rect(SCREEN_WIDTH - 250, 360, 200, 60), RED, "AI", border_color=GRAY
        ),
    ]
    start_button = Button(
        pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 150, 300, 100),
        GREEN,
        "Start Game",
        border_color=GRAY,
        no_background=True,
    )

    running = True
    while running:
        lobby_surf = get_frame_surface(cap_lobby, SCREEN_WIDTH, SCREEN_HEIGHT)
        if lobby_surf:
            screen.blit(lobby_surf, (0, 0))
        else:
            screen.fill(WHITE)

        title = font.render("Choose Characters", True, BLACK)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(title, title_rect)

        p1_font = pygame.font.SysFont(None, 48)
        p1_label = p1_font.render("Player 1", True, BLUE)
        screen.blit(p1_label, (80, 150))
        p2_label = p1_font.render("Player 2", True, RED)
        screen.blit(p2_label, (SCREEN_WIDTH - 250, 150))

        if player1_choice == "durov":
            durov_idle_surf = get_frame_surface(cap_durov_idle, 300, 300)
            if durov_idle_surf:
                screen.blit(durov_idle_surf, (50, 120))
        elif player1_choice == "pepe":
            pepe_idle_surf = get_frame_surface(cap_pepe_idle, 300, 300)
            if pepe_idle_surf:
                screen.blit(pepe_idle_surf, (50, 120))
        if player2_choice == "durov":
            durov_idle_surf = get_frame_surface(cap_durov_idle, 300, 300)
            if durov_idle_surf:
                screen.blit(durov_idle_surf, (SCREEN_WIDTH - 350, 120))
        elif player2_choice == "pepe":
            pepe_idle_surf = get_frame_surface(cap_pepe_idle, 300, 300)
            if pepe_idle_surf:
                screen.blit(pepe_idle_surf, (SCREEN_WIDTH - 350, 120))

        for btn in left_buttons + right_buttons:
            btn.draw(screen)

        start_button.draw(screen)
        shop_button.draw(screen)

        start_anim_surf = get_frame_surface(
            cap_start, start_button.rect.width, start_button.rect.height
        )
        if start_anim_surf:
            sx, sy = start_button.rect.topleft
            screen.blit(start_anim_surf, (sx, sy))

        if player1_choice == "durov":
            pygame.draw.rect(
                screen,
                YELLOW,
                left_buttons[0].rect.inflate(10, 10),
                3,
                border_radius=10,
            )
        elif player1_choice == "pepe":
            pygame.draw.rect(
                screen,
                YELLOW,
                left_buttons[1].rect.inflate(10, 10),
                3,
                border_radius=10,
            )
        else:
            pygame.draw.rect(
                screen,
                YELLOW,
                left_buttons[2].rect.inflate(10, 10),
                3,
                border_radius=10,
            )
        if player2_choice == "durov":
            pygame.draw.rect(
                screen,
                YELLOW,
                right_buttons[0].rect.inflate(10, 10),
                3,
                border_radius=10,
            )
        elif player2_choice == "pepe":
            pygame.draw.rect(
                screen,
                YELLOW,
                right_buttons[1].rect.inflate(10, 10),
                3,
                border_radius=10,
            )
        else:
            pygame.draw.rect(
                screen,
                YELLOW,
                right_buttons[2].rect.inflate(10, 10),
                3,
                border_radius=10,
            )

        for event in pygame.event.get():
            if event.type == QUIT:
                cap_lobby.release()
                cap_start.release()
                cap_durov_idle.release()
                cap_pepe_idle.release()
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()
                if shop_button.is_clicked(pos):
                    shop_screen()
                    cap_lobby.release()
                    cap_start.release()
                    cap_durov_idle.release()
                    cap_pepe_idle.release()
                    cap_lobby = cv2.VideoCapture("лобби.mp4")
                    cap_lobby.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    cap_start = cv2.VideoCapture("start game.mov")
                    cap_start.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    cap_durov_idle = cv2.VideoCapture("дуров стойка галаграмма.mp4")
                    cap_durov_idle.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    cap_pepe_idle = cv2.VideoCapture("пепе стойка галограмма.mp4")
                    cap_pepe_idle.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    assets["video_lobby"] = cap_lobby
                    assets["video_start"] = cap_start
                    assets["video_durov_idle"] = cap_durov_idle
                    assets["video_pepe_idle"] = cap_pepe_idle
                for i, btn in enumerate(left_buttons):
                    if btn.is_clicked(pos):
                        if i == 0:
                            player1_choice = "durov"
                        elif i == 1:
                            player1_choice = "pepe"
                        elif i == 2:
                            player1_choice = "ai"
                for i, btn in enumerate(right_buttons):
                    if btn.is_clicked(pos):
                        if i == 0:
                            player2_choice = "durov"
                        elif i == 1:
                            player2_choice = "pepe"
                        elif i == 2:
                            player2_choice = "ai"
                if start_button.is_clicked(pos):
                    cap_lobby.release()
                    cap_start.release()
                    cap_durov_idle.release()
                    cap_pepe_idle.release()
                    main_game(player1_choice, player2_choice, assets)
                    cap_lobby = cv2.VideoCapture("лобби.mp4")
                    cap_lobby.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    cap_start = cv2.VideoCapture("start game.mov")
                    cap_start.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    cap_durov_idle = cv2.VideoCapture("дуров стойка галаграмма.mp4")
                    cap_durov_idle.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    cap_pepe_idle = cv2.VideoCapture("пепе стойка галограмма.mp4")
                    cap_pepe_idle.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    assets["video_lobby"] = cap_lobby
                    assets["video_start"] = cap_start
                    assets["video_durov_idle"] = cap_durov_idle
                    assets["video_pepe_idle"] = cap_pepe_idle

        pygame.display.flip()
        clock.tick(FPS)


def main():
    assets = load_all_assets()
    main_menu(assets)


if __name__ == "__main__":
    main()
