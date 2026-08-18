"""
WritingsReader — Database layer (PostgreSQL + async SQLAlchemy)
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ──────────────────────────────────────────────
# Connection
# ──────────────────────────────────────────────

DATABASE_URL = "postgresql+asyncpg://raffi@localhost/writingsreader"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)


# ──────────────────────────────────────────────
# ORM Models
# ──────────────────────────────────────────────


class Base(DeclarativeBase):
    pass


class Prompt(Base):
    __tablename__ = "prompts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    emotion: Mapped[str] = mapped_column(String(32), nullable=False)
    theme: Mapped[str] = mapped_column(String(128), nullable=False)

    writings: Mapped[list["Writing"]] = relationship(back_populates="prompt")


class Writing(Base):
    __tablename__ = "writings"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    prompt_id: Mapped[str] = mapped_column(ForeignKey("prompts.id"), nullable=False)
    author_id: Mapped[str] = mapped_column(String(128), nullable=False)
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_mature: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    prompt: Mapped["Prompt"] = relationship(back_populates="writings")
    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="writing")


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        UniqueConstraint("device_id", "writing_id", name="uq_device_writing"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    device_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    writing_id: Mapped[str] = mapped_column(
        ForeignKey("writings.id"), nullable=False, index=True
    )

    writing: Mapped["Writing"] = relationship(back_populates="bookmarks")


class DevicePreference(Base):
    __tablename__ = "device_preferences"

    device_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    is_adult: Mapped[bool] = mapped_column(Boolean, default=False)


# ──────────────────────────────────────────────
# Lifecycle helpers
# ──────────────────────────────────────────────


async def create_tables():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def seed_db():
    """Insert seed data if the DB is empty."""
    async with async_session() as session:
        # Check if prompts already exist — skip seeding if so.
        result = await session.execute(select(Prompt).limit(1))
        if result.scalar_one_or_none() is not None:
            print("   ↳ Seed data already exists, skipping.")
            return

        author = "seed-author-device-001"

        prompts = [
            Prompt(id="prompt-angry", emotion="angry", theme="Broke a Promise"),
            Prompt(id="prompt-joy", emotion="joy", theme="Found a Letter"),
            Prompt(id="prompt-sad", emotion="sad", theme="Lost a Friend"),
        ]
        session.add_all(prompts)

        writings = [
            Writing(
                id="writing-1",
                title="The Quiet Room",
                prompt_id="prompt-sad",
                author_id=author,
                full_text=(
                    "There is a room in my grandmother's house that no one uses anymore.\n"
                    "It sits at the end of a narrow hallway, behind a door that swells shut in the summer heat.\n"
                    "The wallpaper is the color of old tea, peeling at the seams like a secret losing its grip.\n\n"
                    "I found it when I was nine, on a rainy afternoon when the rest of the family "
                    "was loud with laughter in the kitchen. I pushed the door open and stepped inside, "
                    "and the noise behind me became a distant hum.\n\n"
                    "A single window faced the garden. Rain slid down the glass in slow, crooked lines. "
                    "There was a chair, a small table, and a stack of books so old their spines had turned to dust. "
                    "I sat down. I didn't read. I just listened to the rain and felt, for the first time, "
                    "that being alone was not the same as being lonely.\n\n"
                    "I returned to that room every summer until I was sixteen. It became my cathedral, "
                    "my library, my therapist. The silence in there was not empty — it was full of permission. "
                    "Permission to think slowly, to feel without explaining, to simply exist without performing."
                ),
            ),
            Writing(
                id="writing-2",
                title="Morning on the Plateau",
                prompt_id="prompt-joy",
                author_id=author,
                full_text=(
                    "We reached the plateau just before dawn.\n"
                    "The trail had been brutal — six hours of switchbacks through pine forest "
                    "that smelled of cold sap and wet stone.\n"
                    "My legs burned. My pack straps had carved grooves into my shoulders.\n\n"
                    "And then the trees ended, and the world opened.\n\n"
                    "The plateau stretched out like a table set for giants. "
                    "The grass was silver with frost, and the sky was that impossible shade of blue "
                    "that only exists in the minutes before the sun arrives — "
                    "not quite night, not quite day, but something in between.\n\n"
                    "I dropped my pack and stood there, breathing hard, watching my breath "
                    "turn into small clouds that drifted toward the valley below. "
                    "And then the sun crested the ridge. It didn't rise — it arrived, "
                    "all at once, a flood of gold that poured across the plateau and turned "
                    "every blade of frosted grass into a tiny torch.\n\n"
                    "I had seen sunrises before. But I had never seen light like that. "
                    "It felt less like illumination and more like a sound — "
                    "a deep, resonant chord that vibrated through the ground and into my chest."
                ),
            ),
            Writing(
                id="writing-3",
                title="Letters I Never Sent",
                prompt_id="prompt-angry",
                author_id="seed-author-device-002",
                full_text=(
                    "I keep a box under my bed filled with letters I never sent.\n"
                    "Some are addressed to people I loved. Some to people I wronged.\n"
                    "One is addressed to myself, age fourteen, sitting on the bathroom floor "
                    "at three in the morning, convinced the world would be easier without me.\n\n"
                    "That letter is four pages long. I wrote it on a Tuesday night "
                    "after a therapy session that cracked something open inside my ribs. "
                    "I told fourteen-year-old me about the apartment I would rent at twenty-three, "
                    "the one with the big window that faces the park. I told her about the dog, "
                    "the coffee shop on the corner, the friend who calls every Sunday.\n\n"
                    "I told her that the heaviness doesn't disappear, but it becomes something "
                    "you can carry. Like a stone in your pocket — you learn to walk with the weight.\n\n"
                    "I never sent the letter, of course. You can't mail something to the past. "
                    "But writing it was the closest thing to time travel I have ever experienced. "
                    "For a few minutes, I was in both places at once — the bathroom floor and the desk — "
                    "and I could feel the distance between them like a bridge I had built "
                    "with nothing but stubbornness and time."
                ),
            ),
            Writing(
                id="writing-4",
                title="Burnt Bridges",
                prompt_id="prompt-angry",
                author_id=author,
                full_text=(
                    "You said you'd be there. You promised.\n"
                    "Not in the casual way people toss out promises like loose change. "
                    "You looked me in the eye and made me believe it.\n\n"
                    "I built plans around that promise. I rearranged my entire week. "
                    "I told other people no because I had already said yes to you.\n\n"
                    "And then the text came. Two lines. An excuse so thin I could see "
                    "through it like tracing paper. Something came up. Maybe next time.\n\n"
                    "There won't be a next time. Not because I'm dramatic, "
                    "but because trust is not a renewable resource. You spend it once, "
                    "and when it's gone, it's gone."
                ),
            ),
            Writing(
                id="writing-5",
                title="The Garden After Rain",
                prompt_id="prompt-joy",
                author_id="seed-author-device-003",
                full_text=(
                    "I found the letter tucked inside a library book.\n"
                    "It was written on yellow legal paper, folded twice, "
                    "and addressed to no one in particular.\n\n"
                    "Dear Stranger, it began. I hope you're having a good day. "
                    "If not, I want you to know that the garden behind my house "
                    "bloomed this morning after three weeks of rain, and the roses "
                    "are the exact shade of pink that makes you believe the world "
                    "is trying its best.\n\n"
                    "I stood in the garden for twenty minutes. The soil was soft "
                    "under my bare feet. A bird landed on the fence and watched me "
                    "like I was the most interesting thing it had seen all week.\n\n"
                    "I don't know who you are. But I know you're holding this letter, "
                    "and that means something connected us across time and shelves "
                    "and the quiet patience of a book waiting to be opened."
                ),
            ),
            Writing(
                id="writing-6",
                title="Empty Chair",
                prompt_id="prompt-sad",
                author_id="seed-author-device-002",
                full_text=(
                    "There's an empty chair at the kitchen table.\n"
                    "We never moved it. It's been two years and the chair "
                    "still sits there, pushed in at exactly the angle he left it.\n\n"
                    "Sometimes I set a plate there by accident. Muscle memory "
                    "is a cruel kind of love — it remembers what the mind "
                    "is trying to forget.\n\n"
                    "My mother dusts that chair every Sunday. She doesn't "
                    "talk about it. She just runs the cloth along the back, "
                    "the arms, the legs, as if she's tending a grave "
                    "that happens to be made of oak."
                ),
            ),
            Writing(
                id="writing-7",
                title="Kitchen Light",
                prompt_id="prompt-joy",
                author_id=author,
                full_text=(
                    "She left the kitchen light on for me.\n"
                    "It was past midnight when I came home. The house was dark "
                    "except for that one square of gold spilling from the window "
                    "into the yard.\n\n"
                    "On the counter: a plate covered in foil, still warm. "
                    "A glass of water. A note that said only: Eat.\n\n"
                    "I sat at the table alone and cried into my dinner. "
                    "Not from sadness. From the overwhelming weight of being "
                    "known by someone so completely that they anticipate "
                    "your hunger before you feel it yourself."
                ),
            ),
            Writing(
                id="writing-8",
                title="The Apology",
                prompt_id="prompt-angry",
                author_id="seed-author-device-003",
                full_text=(
                    "You apologized like it was a chore.\n"
                    "Like the words were heavy furniture you had to move "
                    "out of your way to get to the door.\n\n"
                    "I'm sorry, you said, but your eyes were already "
                    "past me, already planning your exit. The sorry "
                    "landed on the floor between us like a crumpled receipt.\n\n"
                    "A real apology is a room you sit in. You don't just "
                    "walk through it. You stay. You look at the damage. "
                    "You ask what needs fixing. You pick up a broom.\n\n"
                    "But you were already gone before the echo faded."
                ),
            ),
            Writing(
                id="writing-9",
                title="Old Photographs",
                prompt_id="prompt-sad",
                author_id=author,
                full_text=(
                    "I found a box of photographs in the closet.\n"
                    "Most of them are from a summer I barely remember — "
                    "a lake, a cabin, people laughing around a bonfire.\n\n"
                    "In one photo, I'm sitting on someone's shoulders. "
                    "I'm maybe four years old. My hands are covering "
                    "someone's eyes and we're both laughing so hard "
                    "our faces are blurred.\n\n"
                    "I don't remember who's holding me. I turned the photo "
                    "over looking for a name, but the back is blank. "
                    "Someone loved me enough to carry me, and I can't "
                    "even remember their face.\n\n"
                    "That's the part of loss no one warns you about — "
                    "it's not just the people who leave. It's the memories "
                    "that leave with them."
                ),
            ),
            Writing(
                id="writing-10",
                title="Sunday Morning",
                prompt_id="prompt-joy",
                author_id="seed-author-device-002",
                full_text=(
                    "Sunday morning. No alarm.\n"
                    "The light comes in sideways through the curtains "
                    "and paints a stripe of gold across the bed.\n\n"
                    "The coffee maker clicks on downstairs — I set it "
                    "the night before, the one small act of kindness "
                    "past-me does for future-me.\n\n"
                    "I lie there for ten minutes listening to the house "
                    "breathe. The radiator ticks. The cat jumps onto "
                    "the bed and curls into the crook of my knee.\n\n"
                    "Nothing is happening. That's the whole point. "
                    "Nothing is happening and it is more than enough."
                ),
            ),
            Writing(
                id="writing-11",
                title="A bad day",
                prompt_id="prompt-angry",
                author_id="seed-author-device-004",
                is_mature=True,
                full_text=(
                    "This is a test writing with profanity.\n"
                    "Sometimes everything goes wrong and you just want to say shit.\n"
                    "Fuck it, let's see if the filter works."
                ),
            ),
        ]
        session.add_all(writings)

        await session.commit()
        print("   ↳ Seeded 3 prompts and 10 writings.")
