import pygame
from pygame.locals import *
import sys
import random
import time

pygame.init()

SCREEN_WIDTH = 1080
SCREEN_HEIGHT = 800
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


class Button:
    def __init__(self, rect, color, text, text_color=WHITE, border_color=GRAY):
        self.rect = rect
        self.color = color
        self.text = text
        self.text_color = text_color
        self.border_color = border_color
        self.font = pygame.font.SysFont(None, 36)

    def draw(self, surface):
        pygame.draw.rect(
            surface, self.border_color, self.rect.inflate(10, 10), border_radius=10
        )
        pygame.draw.rect(surface, self.color, self.rect, border_radius=10)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


#
# Bullet теперь принимает аргумент bullet_type ("ton" или "pepe"),
# чтобы решать, когда переворачивать кадры.
#
class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, owner, animation_frames, bullet_type):
        super().__init__()
        self.animation_frames = animation_frames
        self.current_frame = 0
        self.bullet_type = bullet_type

        # Если "ton" -> по умолчанию расчитан на полёт вправо,
        # и если direction < 0 (летим влево) - переворачиваем кадры.
        if self.bullet_type == "ton" and direction < 0:
            self.animation_frames = [
                pygame.transform.flip(frame, True, False)
                for frame in self.animation_frames
            ]

        # Если "pepe" -> по умолчанию расчитан на полёт влево,
        # и если direction > 0 (летим вправо) - переворачиваем кадры.
        if self.bullet_type == "pepe" and direction < 0:
            self.animation_frames = [
                pygame.transform.flip(frame, True, False)
                for frame in self.animation_frames
            ]

        self.image = self.animation_frames[self.current_frame]
        self.rect = self.image.get_rect()

        # Начальные координаты создадим со случайными смещениями, как было
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
    def __init__(self, x, y, animation_frames, jump_frames, hit_frames, is_pepe=False):
        super().__init__()
        self.is_pepe = is_pepe
        self.animation_frames = animation_frames
        self.jump_frames = jump_frames
        self.hit_frames = hit_frames
        self.current_frame = 0
        self.jump_frame = 0
        self.hit_frame = 0
        self.animation_speed = 1.05
        self.frame_counter = 0
        self.image = self.animation_frames[self.current_frame]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        self.mask = pygame.mask.from_surface(self.image)
        self.health = 100
        self.speed = 5
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
        self.mask = pygame.mask.from_surface(self.image)

    #
    # Обратите внимание: передаём bullet_animation_frames
    # И bullet_type определяем ниже.
    #
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

            # Генерируем 3 пули
            for i in range(3):
                bullet = Bullet(
                    self.rect.centerx,
                    self.rect.centery - 10 + i * 10,
                    direction,
                    self,
                    bullet_animation_frames,
                    bullet_type=bullet_type,  # <-- Тип пули ("ton" или "pepe")
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
        # Переворачиваем все кадры (run, jump, hit) и текущую картинку
        self.animation_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.animation_frames
        ]
        self.jump_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.jump_frames
        ]
        self.hit_frames = [
            pygame.transform.flip(frame, True, False) for frame in self.hit_frames
        ]
        self.image = self.animation_frames[self.current_frame]
        self.mask = pygame.mask.from_surface(self.image)

    def gravity_helper(self):
        self.dy += self.gravity
        self.rect.y += self.dy
        if self.rect.bottom >= SCREEN_HEIGHT:
            self.rect.bottom = SCREEN_HEIGHT
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


def create_pepe_animation(folder, frame_count, prefix, width=100, height=100):
    frames = []
    for i in range(frame_count):
        frame_number = str(i).zfill(5)
        image = pygame.image.load(
            f"{folder}/{prefix}_{frame_number}.png"
        ).convert_alpha()
        frames.append(pygame.transform.scale(image, (width, height)))
    return frames


class AIPlayer(Player):
    def inputer(
        self, other, keys, controls, bullets_group, bullet_animation_frames, bullet_type
    ):
        self.is_moving = False

        direction = 1 if other.rect.x > self.rect.x else -1

        if direction == 1:
            if self.rect.x + self.speed < SCREEN_WIDTH - self.rect.width:
                self.rect.x += self.speed
                self.is_moving = True
                if not self.facing_right:
                    self.facing_right = True
                    self.flip_images()
        else:
            if self.rect.x - self.speed > 0:
                self.rect.x -= self.speed
                self.is_moving = True
                if self.facing_right:
                    self.facing_right = False
                    self.flip_images()

        distance = abs(self.rect.x - other.rect.x)
        if distance < 200 and self.on_ground:
            self.dy = self.jump_speed
            self.on_ground = False
            self.is_jumping = True

        current_time = time.time()
        if current_time - self.last_shot_time > 1.5:
            self.last_shot_time = current_time
            for i in range(3):
                bullet = Bullet(
                    self.rect.centerx,
                    self.rect.centery - 10 + i * 10,
                    direction,
                    self,
                    bullet_animation_frames,
                    bullet_type=bullet_type,
                )
                bullets_group.add(bullet)

        if distance < 50 and current_time - self.last_hit_time > 1.5:
            self.is_hitting = True
            self.hit_frame = 0
            self.last_hit_time = current_time
            if self.facing_right:
                self.rect.x += 15
            else:
                self.rect.x -= 15
            if self.rect.colliderect(other.rect):
                other.health -= 10

        self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))


def load_pepe_bullet_animation(folder, frame_count, prefix, width=45, height=45):
    frames = []
    for i in range(frame_count):
        frame_number = str(i).zfill(5)
        image = pygame.image.load(
            f"{folder}/{prefix}_{frame_number}.png"
        ).convert_alpha()
        frames.append(pygame.transform.scale(image, (width, height)))
    return frames


def load_bullet_animation(folder, frame_count, prefix, width=45, height=45):
    frames = []
    for i in range(frame_count):
        frame_number = str(i).zfill(5)
        image = pygame.image.load(
            f"{folder}/{prefix}_{frame_number}.png"
        ).convert_alpha()
        frames.append(pygame.transform.scale(image, (width, height)))
    return frames


def main_game(player1_choice, player2_choice):
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

    #
    #  Локальный AIPlayer, чтобы не менять остальную логику:
    #
    class AIPlayerLocal(AIPlayer):
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
            target_x = other.rect.x + random.randint(-50, 50)

            if abs(self.rect.x - target_x) > 40:
                if direction == 1:
                    self.rect.x += self.speed
                    self.is_moving = True
                    if not self.facing_right:
                        self.facing_right = True
                        self.flip_images()
                else:
                    self.rect.x -= self.speed
                    self.is_moving = True
                    if self.facing_right:
                        self.facing_right = False
                        self.flip_images()

            if random.random() < 0.02 and self.on_ground:
                self.dy = self.jump_speed
                self.on_ground = False
                self.is_jumping = True

            current_time = time.time()
            if current_time - self.last_shot_time > 1.2:
                self.last_shot_time = current_time
                for i in range(3):
                    bullet = Bullet(
                        self.rect.centerx,
                        self.rect.centery - 10 + i * 10,
                        direction,
                        self,
                        bullet_animation_frames,
                        bullet_type=bullet_type,
                    )
                    bullets_group.add(bullet)

            distance = abs(self.rect.x - other.rect.x)
            if distance < 80 and current_time - self.last_hit_time > 2.0:
                self.is_hitting = True
                self.hit_frame = 0
                self.last_hit_time = current_time
                if self.facing_right:
                    self.rect.x += 15
                else:
                    self.rect.x -= 15
                if self.rect.colliderect(other.rect):
                    other.health -= 10

    #
    #  Функции загрузки анимаций (персонажей)
    #
    def load_animation(folder, frame_count, prefix):
        frames = []
        for i in range(frame_count):
            try:
                image = pygame.image.load(
                    f"{folder}/{prefix}_{i+1}.png"
                ).convert_alpha()
            except:
                image = pygame.Surface((125, 125))
                image.fill(ORANGE if "ai" in folder else BLUE)
            frames.append(pygame.transform.scale(image, (125, 125)))
        return frames

    def create_ai_animation(color, frame_count):
        frames = []
        for i in range(frame_count):
            surf = pygame.Surface((125, 125))
            surf.fill(color)
            pygame.draw.rect(surf, BLACK, surf.get_rect(), 3)
            if i % 3 == 0:
                pygame.draw.circle(surf, YELLOW, (60, 60), 15)
            frames.append(surf)
        return frames

    # Player 1 setup
    if player1_choice == "durov":
        player1_frames = load_animation("durov", 19, "дуров бежит")
        player1_jump_frames = load_animation("durov_jump", 49, "durov_jump")
        player1_hit_frames = load_animation("damage_1", 37, "durov_hit")
        p1_is_pepe = False
    elif player1_choice == "pepe":
        player1_frames = create_pepe_animation("pepe_run", 30, "бег пепе")
        player1_jump_frames = create_pepe_animation("pepe_run", 30, "бег пепе")
        player1_hit_frames = create_pepe_animation("hit_pepe_1", 28, "удар пепе 1")
        p1_is_pepe = True
    else:  # AI
        player1_frames = load_animation("durov", 19, "дуров бежит")
        player1_jump_frames = load_animation("durov_jump", 49, "durov_jump")
        player1_hit_frames = load_animation("damage_1", 37, "durov_hit")
        p1_is_pepe = True

    # Player 2 setup
    if player2_choice == "durov":
        player2_frames = load_animation("durov", 19, "дуров бежит")
        player2_jump_frames = load_animation("durov_jump", 49, "durov_jump")
        player2_hit_frames = load_animation("damage_1", 37, "durov_hit")
        p2_is_pepe = False
    elif player2_choice == "pepe":
        player2_frames = create_pepe_animation("pepe_run", 30, "бег пепе")
        player2_jump_frames = create_pepe_animation("pepe_run", 30, "бег пепе")
        player2_hit_frames = create_pepe_animation("hit_pepe_1", 28, "удар пепе 1")
        p2_is_pepe = True
    else:  # AI
        player2_frames = create_pepe_animation("pepe_run", 30, "бег пепе")
        player2_jump_frames = create_pepe_animation("pepe_run", 30, "бег пепе")
        player2_hit_frames = create_pepe_animation("hit_pepe_1", 28, "удар пепе 1")
        p2_is_pepe = True

    #
    #  Подбираем анимацию пуль + bullet_type для каждого
    #
    # 1) Если p1 - Pepe, то "pepe" bullet_type и пули из load_pepe_bullet_animation
    #    Иначе - "ton" bullet_type и пули "ton coin"
    #
    if p1_is_pepe:
        p1_bullet_frames = load_pepe_bullet_animation("pepe coin", 155, "пепе пуля")
        p1_bullet_type = "pepe"  # Переворачивается при полёте вправо
    else:
        p1_bullet_frames = load_bullet_animation("ton coin", 155, "ton coin")
        p1_bullet_type = "ton"  # Переворачивается при полёте влево

    # 2) Аналогично для p2
    if p2_is_pepe:
        p2_bullet_frames = load_pepe_bullet_animation("pepe coin", 155, "пепе пуля")
        p2_bullet_type = "pepe"
    else:
        p2_bullet_frames = load_bullet_animation("ton coin", 155, "ton coin")
        p2_bullet_type = "ton"

    # Создаём игроков
    if player1_choice == "ai":
        player1 = AIPlayerLocal(
            100,
            SCREEN_HEIGHT - 150,
            player1_frames,
            player1_jump_frames,
            player1_hit_frames,
            is_pepe=p1_is_pepe,
        )
    else:
        player1 = Player(
            100,
            SCREEN_HEIGHT - 150,
            player1_frames,
            player1_jump_frames,
            player1_hit_frames,
            is_pepe=p1_is_pepe,
        )

    if player2_choice == "ai":
        player2 = AIPlayerLocal(
            SCREEN_WIDTH - 200,
            SCREEN_HEIGHT - 150,
            player2_frames,
            player2_jump_frames,
            player2_hit_frames,
            is_pepe=p2_is_pepe,
        )
    else:
        player2 = Player(
            SCREEN_WIDTH - 200,
            SCREEN_HEIGHT - 150,
            player2_frames,
            player2_jump_frames,
            player2_hit_frames,
            is_pepe=p2_is_pepe,
        )

    # Группы
    all_sprites = pygame.sprite.Group()
    all_sprites.add(player1, player2)
    bullets = pygame.sprite.Group()

    running = True
    while running:
        screen.fill(WHITE)

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False

        # Получаем глобальное состояние всех клавиш
        keys = pygame.key.get_pressed()

        # Фильтруем только те клавиши, которые используются player1 и player2
        p1_keys = {key: keys[key] for key in player1_controls.values()}
        p2_keys = {key: keys[key] for key in player2_controls.values()}

        # Вызываем у каждого свою update,
        # передавая соответствующие bullet_frames + bullet_type
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

        # Проверяем попадания
        for bullet in bullets:
            if bullet.owner != player1 and pygame.sprite.collide_mask(bullet, player1):
                player1.health = max(0, player1.health - 1)
                bullet.kill()
            if bullet.owner != player2 and pygame.sprite.collide_mask(bullet, player2):
                player2.health = max(0, player2.health - 1)
                bullet.kill()

        # Проверяем победителя
        if player1.health <= 0 or player2.health <= 0:
            running = False

        all_sprites.draw(screen)
        bullets.draw(screen)

        # Отрисовка здоровья
        player1.draw_health_bar(screen, 50, 50)
        player2.draw_health_bar(screen, SCREEN_WIDTH - 150, 50)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


def main_menu():
    font = pygame.font.SysFont(None, 74)
    button_color = BLACK
    border_color = GRAY
    text_color = WHITE

    # Selection variables
    player1_choice = "durov"
    player2_choice = "durov"

    # Left side buttons (Player 1)
    left_buttons = [
        Button(pygame.Rect(50, 200, 200, 60), BLUE, "Durov", border_color=GRAY),
        Button(pygame.Rect(50, 280, 200, 60), BLUE, "pepe", border_color=GRAY),
        Button(pygame.Rect(50, 360, 200, 60), BLUE, "AI", border_color=GRAY),
    ]

    # Right side buttons (Player 2)
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

    # Start button
    start_button = Button(
        pygame.Rect(SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 + 100, 300, 100),
        GREEN,
        "Start Game",
        border_color=GRAY,
    )

    running = True
    while running:
        screen.fill(WHITE)

        # Draw title
        title = font.render("Choose Characters", True, BLACK)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 100))
        screen.blit(title, title_rect)

        # Draw player labels
        p1_font = pygame.font.SysFont(None, 48)
        p1_label = p1_font.render("Player 1", True, BLUE)
        screen.blit(p1_label, (80, 150))

        p2_label = p1_font.render("Player 2", True, RED)
        screen.blit(p2_label, (SCREEN_WIDTH - 250, 150))

        # Draw buttons
        for btn in left_buttons + right_buttons + [start_button]:
            btn.draw(screen)

        # Подсветка выбранных (логика упрощена, но "остальное не менять" – оставим как было)
        pygame.draw.rect(
            screen,
            YELLOW,
            left_buttons[0 if player1_choice == "durov" else 1].rect.inflate(10, 10),
            3,
            border_radius=10,
        )
        pygame.draw.rect(
            screen,
            YELLOW,
            right_buttons[0 if player2_choice == "durov" else 1].rect.inflate(10, 10),
            3,
            border_radius=10,
        )

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                pos = pygame.mouse.get_pos()

                # Check left buttons (Player 1)
                for i, btn in enumerate(left_buttons):
                    if btn.is_clicked(pos):
                        if i == 0:
                            player1_choice = "durov"
                        elif i == 1:
                            player1_choice = "pepe"
                        elif i == 2:
                            player1_choice = "ai"

                # Check right buttons (Player 2)
                for i, btn in enumerate(right_buttons):
                    if btn.is_clicked(pos):
                        if i == 0:
                            player2_choice = "durov"
                        elif i == 1:
                            player2_choice = "pepe"
                        elif i == 2:
                            player2_choice = "ai"

                if start_button.is_clicked(pos):
                    main_game(player1_choice, player2_choice)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main_menu()
