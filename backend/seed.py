from __future__ import annotations

from dotenv import load_dotenv
from sqlalchemy import or_, select

import models
from db import SessionLocal
from security import hash_password


def get_or_create_user(
    db,
    *,
    full_name: str,
    username: str,
    email: str,
    password: str,
    role: models.UserRole,
    school_id: int,
    is_active: bool = True,
) -> models.User:
    normalized_username = username.strip().lower()
    normalized_email = email.strip().lower()
    user = db.scalar(
        select(models.User).where(
            models.User.school_id == school_id,
            or_(
                models.User.username == normalized_username,
                models.User.email == normalized_email,
            ),
        )
    )
    if user:
        user.full_name = full_name
        user.username = normalized_username
        user.role = role
        user.is_active = is_active
        user.email = normalized_email
        user.password_hash = hash_password(password)
        return user
    user = models.User(
        school_id=school_id,
        full_name=full_name,
        username=normalized_username,
        email=normalized_email,
        password_hash=hash_password(password),
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.flush()
    return user


def get_or_create_level(db, *, school_id: int, name: str, sort_order: int) -> models.Level:
    level = db.scalar(
        select(models.Level).where(
            models.Level.school_id == school_id,
            models.Level.name == name,
        )
    )
    if not level:
        level = models.Level(school_id=school_id, name=name, sort_order=sort_order)
        db.add(level)
        db.flush()
    return level


def get_or_create_skill(db, *, level_id: int, name: str, sort_order: int) -> models.Skill:
    skill = db.scalar(
        select(models.Skill).where(
            models.Skill.level_id == level_id,
            models.Skill.name == name,
        )
    )
    if not skill:
        skill = models.Skill(level_id=level_id, name=name, sort_order=sort_order)
        db.add(skill)
        db.flush()
    return skill


def get_or_create_attribute(db, *, school_id: int, name: str) -> models.Attribute:
    attr = db.scalar(
        select(models.Attribute).where(
            models.Attribute.school_id == school_id,
            models.Attribute.name == name,
        )
    )
    if not attr:
        attr = models.Attribute(school_id=school_id, name=name)
        db.add(attr)
        db.flush()
    return attr


def link_skill_attribute(db, *, skill_id: int, attribute_id: int) -> None:
    existing = db.scalar(
        select(models.SkillAttribute).where(
            models.SkillAttribute.skill_id == skill_id,
            models.SkillAttribute.attribute_id == attribute_id,
        )
    )
    if not existing:
        db.add(models.SkillAttribute(skill_id=skill_id, attribute_id=attribute_id))
        db.flush()


CURRICULUM = [
    {
        "name": "Seahorse",
        "sort_order": 1,
        "skills": [
            {
                "name": '"I can put my goggles on"',
                "sort_order": 1,
                "attributes": [
                    "Swimmer is able to put their goggles on by themselves.",
                ],
            },
            {
                "name": "Full Pour-Over",
                "sort_order": 2,
                "attributes": [
                    'Full shower bucket "dump" pour.',
                    "Swimmer enjoys the pour over - no \"shock\" reaction.",
                ],
            },
            {
                "name": "Full Assisted Submersion",
                "sort_order": 3,
                "attributes": [
                    "Swimmer goes all the way underwater.",
                    "Vertical submersion with feet on the ground.",
                    "The swimmer can be holding the instructor's hand, the wall, or lane line.",
                ],
            },
            {
                "name": "Unassisted Retrieve Ring",
                "sort_order": 4,
                "attributes": [
                    "Swimmer fully submerges and retrieves a ring (or other toy) from bottom of the pool.",
                    "No assistance from the instructor. No holding wall or lane line.",
                ],
            },
            {
                "name": "Monkey on the Wall",
                "sort_order": 5,
                "attributes": [
                    "Self-support monkey on the wall.",
                    "Feet on wall, both hands holding, head back.",
                    "Ears must be in the water.",
                ],
            },
            {
                "name": "Assisted Back Float 10",
                "sort_order": 6,
                "attributes": [
                    "Assisted back float for minimum of 10 seconds.",
                    "Two types of assisted float are acceptable.",
                    "Teacher hold - swimmer in starfish position, instructor holding side of body.",
                    "Barbell - swimmer holding barbell across hips.",
                ],
            },
            {
                "name": "Unassisted Back Float",
                "sort_order": 7,
                "attributes": [
                    "Fully independent and confident back float.",
                    "Minimum of 5 seconds.",
                ],
            },
            {
                "name": "Assisted Front Float",
                "sort_order": 8,
                "attributes": [
                    "Starfish position.",
                    "Instructor holding sides of the body.",
                    "Full face submersion for minimum of 3 seconds.",
                    "Swimmer either holding breath or blowing bubbles.",
                ],
            },
            {
                "name": "Unassisted Front Float",
                "sort_order": 9,
                "attributes": [
                    "Fully independent and confident front float.",
                    "Minimum 5 seconds.",
                ],
            },
            {
                "name": "Assisted Safe 'R' Me Step 1",
                "sort_order": 10,
                "attributes": [
                    "Swimmer jumps in with assistance.",
                    "Assistance can be either 1 or 2 hands held.",
                    "Swimmer must fully submerge.",
                    "No goggles.",
                ],
            },
            {
                "name": "Unassisted Safe 'R' Me Step 1",
                "sort_order": 11,
                "attributes": [
                    "Unassisted jump, without reaching to instructor.",
                    "Full submersion.",
                    "Resurfaces independently.",
                    "No goggles.",
                ],
            },
        ],
    },
    {
        "name": "Sea Otter",
        "sort_order": 2,
        "skills": [
            {
                "name": "Practical Swimming",
                "sort_order": 12,
                "attributes": [
                    "Swimmer swims out to the ring, dives down, and retrieves.",
                    "No breath between swimming to ring and diving.",
                    "Swim and retrieval should be in one fluid motion.",
                    "The ring must be minimum 8 feet away from the wall.",
                ],
            },
            {
                "name": "Assisted Back Glide",
                "sort_order": 13,
                "attributes": [
                    "The instructor sets body, head position and pushes swimmer back to the wall.",
                    "The swimmer remains in the correct position and calmly glides back to the wall.",
                    "Must be gliding for at least 3 seconds.",
                ],
            },
            {
                "name": "Unassisted Back Glide",
                "sort_order": 14,
                "attributes": [
                    "Monkey on the wall to start.",
                    "Swimmer pushes away from the wall, assumes the correct body, head, and arm position.",
                    "Glide must be for minimum of 5 seconds.",
                ],
            },
            {
                "name": "Back Kick with Barbell",
                "sort_order": 15,
                "attributes": [
                    "Monkey on the wall to start, barbell under hands.",
                    "Swimmer pushes away from the wall, assumes the correct body, head, and arm position and puts barbell under belly button.",
                    "Swimmer kicks 12 feet (around halfway) in 5 seconds or less.",
                ],
            },
            {
                "name": "Back Kick to Instructor",
                "sort_order": 16,
                "attributes": [
                    "Monkey on the wall to start.",
                    "Swimmer pushes away from the wall, assumes the correct body, head, and arm position.",
                    "Swimmer kicks 12 feet (around halfway) in 5 seconds or less.",
                ],
            },
            {
                "name": "Back Kick to Wall",
                "sort_order": 17,
                "attributes": [
                    "Kicking technique does not have to be perfect, just enough for them to meet the standards so that they will be able to participate in a Pufferfish class.",
                    "The instructor gets swimmer set in the correct head/body position, then lets them kick back to the wall with minimal push.",
                    "No time limit for this activity. Swimmer just needs to make the distance. (12 feet)",
                ],
            },
            {
                "name": "Assisted Front Glide",
                "sort_order": 18,
                "attributes": [
                    "The instructor sets body, head position and pushes swimmer back to the wall.",
                    "The swimmer remains in the correct position and calmly glides back to the wall.",
                    "Must be gliding for at least 3 seconds.",
                ],
            },
            {
                "name": "Unassisted Front Glide",
                "sort_order": 19,
                "attributes": [
                    "Starting from wall, swimmer starts themselves with eyes down and arms out.",
                    "Swimmer glides for 5+ seconds.",
                    "Maintain correct arm and head position throughout.",
                ],
            },
            {
                "name": "Front Kick 12 Feet",
                "sort_order": 20,
                "attributes": [
                    "The swimmer must be able to start themselves and kick in the #11 position 12 feet (a little over halfway down the pool) with no assistance from the instructor.",
                ],
            },
            {
                "name": "Front Kick 12 Feet, Less Than 5 Seconds",
                "sort_order": 21,
                "attributes": [
                    "The swimmer must be able to start themselves and kick in the #11 position for 12 feet (a little over halfway down the pool) with no assistance from the instructor.",
                    "Must be able to cover the distance in 5 seconds or less.",
                ],
            },
            {
                "name": "Safe 'R' Me Step 2 with Goggles",
                "sort_order": 22,
                "attributes": [
                    "Jump from wall, submerge, and swim back immediately without help from the instructor.",
                    "Does not wipe water or hair from face before getting to the wall.",
                    "Goggles may be worn.",
                ],
            },
            {
                "name": "Safe 'R' Me Step 2 No Goggles",
                "sort_order": 23,
                "attributes": [
                    "Jump from wall, submerge, and swim back immediately without help from the instructor.",
                    "Does not wipe water or hair from face before getting to the wall.",
                    "No goggles.",
                ],
            },
        ],
    },
    {
        "name": "Pufferfish",
        "sort_order": 3,
        "skills": [
            {
                "name": "Bobs - Rhythmic Breathing",
                "sort_order": 24,
                "attributes": [
                    "Stay submerged for at least 3 seconds.",
                    "No pause when coming up for a breath - continuous up/down motion.",
                ],
            },
            {
                "name": "Number 11 Front Kick",
                "sort_order": 25,
                "attributes": [
                    "Perform the correct start.",
                    "Remain balanced.",
                    "Maintain the correct head and arm position, with eyes down, arms touching the head behind the ears and extended straight out from the shoulder.",
                    "Maintain a small, fast kick from the hip with relaxed knees and ankles.",
                    "20 feet.",
                ],
            },
            {
                "name": "Back Kick",
                "sort_order": 26,
                "attributes": [
                    "Display proper kicking technique and maintain a consistent, small, fast kick.",
                    "Maintain a horizontal body position.",
                    "Achieve and maintain momentum; Swimmer should be able to kick at least 20 feet in under 5 seconds.",
                    "Head position – eyes straight up, water making a ring around the face from bottom of chin to top of the forehead.",
                    "Be able to achieve back balance soon after pushing off the wall or starting from instructor.",
                    "Keep the knee and ankle joints relaxed and floppy. Foot sweeps up with the top of the leading foot as it reaches the surface.",
                ],
            },
            {
                "name": "1 Up 1 Down Back Kick 20 Feet",
                "sort_order": 27,
                "attributes": [
                    "1 Arm up touching the ear, other arm at the side.",
                    "Display proper kicking technique and maintain a consistent, small, fast kick.",
                    "Maintain a horizontal body position.",
                    "Achieve and maintain momentum; Swimmer should be able to kick at least 20 feet in under 5 seconds.",
                    "Head position – eyes straight up, water making a ring around the face from bottom of chin to top of the forehead.",
                    "Be able to achieve back balance soon after pushing off the wall or starting from instructor.",
                    "Keep the knee and ankle joints relaxed and floppy. Foot sweeps up with the top of the leading foot as it reaches the surface.",
                ],
            },
            {
                "name": "Unassisted Rollover",
                "sort_order": 28,
                "attributes": [
                    "Swimmer is able to perform a front to back roll in Body Roll Kick well enough to stay on their back to take a breath without sinking underwater within 5 seconds of their roll.",
                    "The arm up doesn't drop to their side or past a 90 degree angle from the head.",
                    "Swimmer should be able to continue forward progress.",
                    "Simply a safety skill.",
                ],
            },
            {
                "name": "Body Roll Kick 24 Feet",
                "sort_order": 29,
                "attributes": [
                    "Maintain balance and momentum on both front and back before/after the body roll – feet should remain at or close to the surface, and if below the surface, swimmer recovers within 3 seconds.",
                    "Display proper kicking technique and maintain a consistent, small, fast kick.",
                    "Roll using hips and shoulders, little to no head movement before/during/after roll.",
                    "Stays 3 seconds on front, 3 on back.",
                    "24 feet.",
                ],
            },
            {
                "name": "Standing Freestyle Arms",
                "sort_order": 30,
                "attributes": [
                    "Keep their arms straight.",
                    "Rotate torso side to side in rhythm with arm strokes.",
                    "Keep head still looking straight forward.",
                    "Arms brush their hip on the way down, and ear on the way up.",
                ],
            },
            {
                "name": "Basic Freestyle - Kick Coordination/Propulsion",
                "sort_order": 31,
                "attributes": [
                    "Swimmer maintains a consistent kick for the entire distance.",
                    "Without disrupting or changing their kick, the swimmer completes 4 arm strokes (though timing and technique of arms do not have to be correct).",
                ],
            },
            {
                "name": "Basic Freestyle - Arm Stroke Coordination",
                "sort_order": 32,
                "attributes": [
                    "Swim with proper head position and horizontal body balance.",
                    "Display proper kicking technique and consistent kick.",
                    "Pulling the full length on arm strokes (head to hip pull with hand).",
                    "Coordinate arm and leg movement together – neither element suffers. (4 Arms)",
                    "Gentle hand entry with no excessive splashing or slapping the water.",
                    "Head stays still, with the eyes down and top of head pointing in the direction the swimmer is going.",
                    "Closed or nearly closed fingers during arm strokes.",
                    "Blow bubbles.",
                ],
            },
            {
                "name": "Basic Catch-Up Freestyle",
                "sort_order": 33,
                "attributes": [
                    "Everything from above milestone skills.",
                    'Maintain correct "catch-up" arm timing throughout. Return to #11 position after each arm stroke. (at least 4 arm strokes)',
                ],
            },
            {
                "name": "Safe 'R' Me Step 3",
                "sort_order": 34,
                "attributes": [
                    "Jump in, come up to float on their back for 5 seconds, and return to the wall.",
                ],
            },
        ],
    },
    {
        "name": "Octopus",
        "sort_order": 4,
        "skills": [
            {
                "name": "Body Roll Kick 30 Feet",
                "sort_order": 35,
                "attributes": [
                    "Maintain balance and momentum on both front and back before/after the body roll – feet should remain at or close to the surface.",
                    "Display proper kicking technique and maintain a consistent, small, fast kick.",
                    "Roll using hips and shoulders. Little to no head movement before/during/after roll.",
                    "Stays 3 seconds on front, 3 on back.",
                    "Perform at least 2 full cycles rolling to alternating sides.",
                    "Distance of 30 feet.",
                ],
            },
            {
                "name": "Basic Rock n Roll Freestyle",
                "sort_order": 36,
                "attributes": [
                    "Swimmer is able to count 3 arm strokes and roll to their back without losing balance or momentum.",
                    "Swim with correct body position and balance.",
                    "Consistent, proper kick, including during roll.",
                    "Full strokes, reaching as far forward as possible and as far back as possible.",
                    'Perform a "catch-up" stroke with one hand always out in front.',
                    "Rolling as the arm reaches the ear and extends forward (as in a freestyle side breath).",
                    "Swimmer holds Roll arm straight up by their head during the roll and while they're on their back.",
                    "Straight arms with fingers closed or nearly closed.",
                ],
            },
            {
                "name": "Continuous Rock n Roll Freestyle",
                "sort_order": 37,
                "attributes": [
                    "Swim with correct body position and balance.",
                    "Consistent, proper kick, including during roll.",
                    "Full strokes, reaching as far forward as possible and as far back as possible.",
                    'Perform a "catch-up" stroke with one hand always out in front.',
                    "Rolling as the arm reaches the ear and extends forward (as in a freestyle side breath).",
                    "Blowing bubbles (not holding breath). Watch for bubbles by the ears, go underwater and watch bubbles, look to see if the swimmer exhales when they roll to their back.",
                    "Coordinating arms and body roll with 'Rock and Roll' count – Arm pushes the face back into the water.",
                    "Swimmer holds Roll arm straight up by their head during the roll and while they're on their back.",
                    "Straight arms with fingers closed or nearly closed.",
                ],
            },
            {
                "name": "Standing Side Breathing",
                "sort_order": 38,
                "attributes": [
                    "Head close to fully submerged while blowing bubbles.",
                    "Head and shoulders start turning to the side immediately after the breathing hand drops off the lane rope to perform the arm stroke.",
                    "Ear on shoulder/Head low in the water during breath (head should be partially submerged).",
                    "Face enters the water before the arm returns to the lane rope.",
                    "Small, fast breath keeping with the timing.",
                    "Correctly counting 3 arm strokes before breathing.",
                ],
            },
            {
                "name": "1 Up 1 Down Back Kick 30 Feet",
                "sort_order": 39,
                "attributes": [
                    "1 Arm up touching the ear, other arm at the side.",
                    "Display proper kicking technique and maintain a consistent, small, fast kick.",
                    "Knees should stay below the surface while feet make a small splash on each kick.",
                    "Head position – eyes straight up, water making a ring around the face from bottom of chin to top of the forehead.",
                    "Be able to achieve back balance soon after pushing off the wall or starting from instructor.",
                    "Keep the knee and ankle joints relaxed and floppy. Foot sweeps up with the top of the leading foot as it reaches the surface.",
                    "This needs to be done back to the instructor with no push.",
                ],
            },
            {
                "name": "Backstroke Arm Strokes",
                "sort_order": 40,
                "attributes": [
                    "Complete the pull all the way to the hip.",
                    "Hand enters above the head.",
                    "Underwater pull comes down the sides of swimmer's body. No underwater scooping motion.",
                    "Stroke with straight arms above the water.",
                    "Hand exits with the thumb first after the pull, and enters pinky-first.",
                ],
            },
            {
                "name": "Basic Backstroke",
                "sort_order": 41,
                "attributes": [
                    "Maintain horizontal balance throughout activity.",
                    "Keep a consistent, proper kick with feet coming up to the surface.",
                    "Simultaneous arm tempo: arms do not stop at the hips.",
                    "Complete the pull all the way to the hip.",
                    "Hand enters above the head.",
                    "Stroke with straight arms above the water.",
                    "Hand exits with the thumb first after the pull, and enters pinky-first.",
                    "Swims in a straight line.",
                ],
            },
            {
                "name": "Treading Water 10 Seconds",
                "sort_order": 42,
                "attributes": [
                    "Maintain a vertical body position with the head above water.",
                    "Comfortably remain in this position for at least 10 seconds.",
                ],
            },
            {
                "name": "Treading Water 30 Seconds",
                "sort_order": 43,
                "attributes": [
                    "Maintain a vertical body position with the head above water.",
                    "Comfortably remain in this position for at least 30 seconds.",
                ],
            },
        ],
    },
    {
        "name": "Spotted Eagle Ray",
        "sort_order": 5,
        "skills": [
            {
                "name": "Freestyle Side Breathing Technique",
                "sort_order": 44,
                "attributes": [
                    "Swimmer demonstrates the ability to consistently take a breath to the side by turning the body and head with no upward movement of the head.",
                    "Breathe by turning their hips and shoulders to the side with minimal head movement.",
                    "Proper air exchange/rhythmic breathing - blowing bubbles underwater, taking small fast breaths, arm does not stop during the pull/recovery.",
                    "Timing of breathing and arms – Begin the body rotation as soon as the hand drops to begin pull. Face goes back into the water just before the hand fully recovers back to the front.",
                ],
            },
            {
                "name": "Freestyle Continuous Flutter Kick",
                "sort_order": 45,
                "attributes": [
                    "During the freestyle activity, swimmer demonstrates the ability to maintain a steady small, fast flutter kick from start to finish, especially while breathing.",
                ],
            },
            {
                "name": "Catch-Up Freestyle Swimming",
                "sort_order": 46,
                "attributes": [
                    "Maintain a steady kick throughout the entire activity, especially when breathing.",
                    "Follow the correct 3 strokes & breathe pattern.",
                    "Breathe by turning their hips and shoulders to the side with minimal head movement.",
                    "Timing of breathing and arms – Begin the body rotation as soon as the hand begins the pull. Face goes back into the water just before the hand fully recovers back to the noodle.",
                    "Proper Air Exchange: blowing bubbles underwater, taking small fast breaths, arm does not stop (it can/will slow down) during the pull/recovery. Swimmer should not be huffing and puffing after or during the activity.",
                    "Pull: Fingers not wide open, pulling full range of motion (as far forward and as far back as possible), and keeping the arms straight the whole time.",
                ],
            },
            {
                "name": "Rotated 1 Up 1 Down Back Kick",
                "sort_order": 47,
                "attributes": [
                    "One arm up touching the head, just behind the ear. Opposite arm at side.",
                    "Swimmer remains in rotated position with shoulder visible at surface, hips turned slightly.",
                    "Kick should not be up and down, but slightly sideways.",
                    "Maintain proper head position. Swimmer does not tilt head to touch arm.",
                ],
            },
            {
                "name": "Backstroke",
                "sort_order": 48,
                "attributes": [
                    "Everything from Octopus Basic Backstroke AND:",
                    "Proper hand entry – Pinky finger enters first, hand is outside the shoulder line.",
                    "Proper body rotation – shoulder clears the water before the hand comes out of the water.",
                ],
            },
            {
                "name": "Butterfly Dolphin Kick",
                "sort_order": 49,
                "attributes": [
                    "Relaxed, undulating body position through entire activity.",
                    "Keep feet together (or close to touching).",
                    "Proper undulation, starting with pushing the head and chest down at the same time as the feet push down.",
                    "Return to the horizontal body position at the surface of the water between each pulse.",
                ],
            },
            {
                "name": "Basic Breaststroke Kick",
                "sort_order": 50,
                "attributes": [
                    "Show a kick that begins and ends with legs straight and squeezed together.",
                    "Move the feet/legs symmetrically together throughout kick.",
                    "Turn feet out at some point during the kick, the feet do not have to remain turned out through the whole kicking phase.",
                    "Repeat the above actions for at least 3 consecutive kicks.",
                    "Swimmer must maintain forward progress generated from the kick during the 3 consecutive kicks.",
                ],
            },
            {
                "name": "Sitting Dive",
                "sort_order": 51,
                "attributes": [
                    "Maintain a tight streamline position throughout dive and glide.",
                    "Enter the water at an angle that takes the body under the water so that the swimmer glides just below the surface of the water.",
                ],
            },
            {
                "name": "Somersault",
                "sort_order": 52,
                "attributes": [
                    "Perform a full somersault underwater.",
                    "Knees tucked into chest.",
                    "Head must be tucked into chest.",
                    "Little to no help from arms.",
                    "Blow bubbles out of the nose and not get water in their nose.",
                ],
            },
        ],
    },
]


def seed_curriculum(db, school_id: int) -> None:
    for level_data in CURRICULUM:
        level = get_or_create_level(
            db,
            school_id=school_id,
            name=level_data["name"],
            sort_order=level_data["sort_order"],
        )
        for skill_data in level_data["skills"]:
            skill = get_or_create_skill(
                db,
                level_id=level.id,
                name=skill_data["name"],
                sort_order=skill_data["sort_order"],
            )
            for attr_name in skill_data["attributes"]:
                attr = get_or_create_attribute(db, school_id=school_id, name=attr_name)
                link_skill_attribute(db, skill_id=skill.id, attribute_id=attr.id)


# Evaluations from Sample_Trainee_Evaluations.csv — 2 per level
SAMPLE_EVALUATIONS = [
    # Seahorse
    {
        "level": "Seahorse", "skill": "Full Pour-Over",
        "instructor": "alex@propel.local", "supervisor": "casey@propel.local",
        "ratings": [
            ('Full shower bucket "dump" pour.', 4),
            ('Swimmer enjoys the pour over - no "shock" reaction.', 5),
        ],
    },
    {
        "level": "Seahorse", "skill": "Unassisted Back Float",
        "instructor": "jordan@propel.local", "supervisor": "taylor@propel.local",
        "ratings": [
            ("Fully independent and confident back float.", 3),
            ("Minimum of 5 seconds.", 3),
        ],
    },
    # Sea Otter
    {
        "level": "Sea Otter", "skill": "Practical Swimming",
        "instructor": "alex@propel.local", "supervisor": "taylor@propel.local",
        "ratings": [
            ("Swimmer swims out to the ring, dives down, and retrieves.", 5),
            ("No breath between swimming to ring and diving.", 5),
            ("Swim and retrieval should be in one fluid motion.", 4),
            ("The ring must be minimum 8 feet away from the wall.", 5),
        ],
    },
    {
        "level": "Sea Otter", "skill": "Unassisted Back Glide",
        "instructor": "jordan@propel.local", "supervisor": "casey@propel.local",
        "ratings": [
            ("Monkey on the wall to start.", 2),
            ("Swimmer pushes away from the wall, assumes the correct body, head, and arm position.", 2),
            ("Glide must be for minimum of 5 seconds.", 3),
        ],
    },
    # Pufferfish
    {
        "level": "Pufferfish", "skill": "Bobs - Rhythmic Breathing",
        "instructor": "alex@propel.local", "supervisor": "casey@propel.local",
        "ratings": [
            ("Stay submerged for at least 3 seconds.", 4),
            ("No pause when coming up for a breath - continuous up/down motion.", 4),
        ],
    },
    {
        "level": "Pufferfish", "skill": "Back Kick",
        "instructor": "jordan@propel.local", "supervisor": "taylor@propel.local",
        "ratings": [
            ("Display proper kicking technique and maintain a consistent, small, fast kick.", 5),
            ("Maintain a horizontal body position.", 5),
            ("Achieve and maintain momentum; Swimmer should be able to kick at least 20 feet in under 5 seconds.", 5),
            ("Keep the knee and ankle joints relaxed and floppy. Foot sweeps up with the top of the leading foot as it reaches the surface.", 4),
        ],
    },
    # Octopus
    {
        "level": "Octopus", "skill": "Body Roll Kick 30 Feet",
        "instructor": "alex@propel.local", "supervisor": "taylor@propel.local",
        "ratings": [
            ("Maintain balance and momentum on both front and back before/after the body roll – feet should remain at or close to the surface.", 3),
            ("Roll using hips and shoulders. Little to no head movement before/during/after roll.", 3),
            ("Stays 3 seconds on front, 3 on back.", 2),
            ("Distance of 30 feet.", 3),
        ],
    },
    {
        "level": "Octopus", "skill": "Basic Rock n Roll Freestyle",
        "instructor": "jordan@propel.local", "supervisor": "casey@propel.local",
        "ratings": [
            ("Swimmer is able to count 3 arm strokes and roll to their back without losing balance or momentum.", 4),
            ('Perform a "catch-up" stroke with one hand always out in front.', 5),
            ("Full strokes, reaching as far forward as possible and as far back as possible.", 4),
        ],
    },
    # Spotted Eagle Ray
    {
        "level": "Spotted Eagle Ray", "skill": "Freestyle Side Breathing Technique",
        "instructor": "alex@propel.local", "supervisor": "casey@propel.local",
        "ratings": [
            ("Swimmer demonstrates the ability to consistently take a breath to the side by turning the body and head with no upward movement of the head.", 5),
            ("Proper air exchange/rhythmic breathing - blowing bubbles underwater, taking small fast breaths, arm does not stop during the pull/recovery.", 5),
            ("Timing of breathing and arms – Begin the body rotation as soon as the hand drops to begin pull. Face goes back into the water just before the hand fully recovers back to the front.", 5),
        ],
    },
    {
        "level": "Spotted Eagle Ray", "skill": "Catch-Up Freestyle Swimming",
        "instructor": "jordan@propel.local", "supervisor": "taylor@propel.local",
        "ratings": [
            ("Maintain a steady kick throughout the entire activity, especially when breathing.", 1),
            ("Follow the correct 3 strokes & breathe pattern.", 2),
            ("Breathe by turning their hips and shoulders to the side with minimal head movement.", 2),
        ],
    },
]


def seed_sample_evaluations(db, school_id: int) -> int:
    created = 0
    for ev in SAMPLE_EVALUATIONS:
        instructor = db.scalar(
            select(models.User).where(
                models.User.school_id == school_id,
                models.User.email == ev["instructor"],
            )
        )
        supervisor = db.scalar(
            select(models.User).where(
                models.User.school_id == school_id,
                models.User.email == ev["supervisor"],
            )
        )
        skill = db.scalar(
            select(models.Skill)
            .join(models.Level, models.Skill.level_id == models.Level.id)
            .where(
                models.Level.school_id == school_id,
                models.Level.name == ev["level"],
                models.Skill.name == ev["skill"],
            )
        )
        if not instructor or not supervisor or not skill:
            print(f"  SKIP: missing data for {ev['level']} / {ev['skill']}")
            continue

        # Skip if already seeded (same instructor + supervisor + skill)
        existing = db.scalar(
            select(models.Evaluation).where(
                models.Evaluation.instructor_id == instructor.id,
                models.Evaluation.supervisor_id == supervisor.id,
                models.Evaluation.skill_id == skill.id,
            )
        )
        if existing:
            continue

        evaluation = models.Evaluation(
            school_id=school_id,
            instructor_id=instructor.id,
            supervisor_id=supervisor.id,
            skill_id=skill.id,
        )
        db.add(evaluation)
        db.flush()

        ratings = []
        for attr_name, rating in ev["ratings"]:
            attr = db.scalar(
                select(models.Attribute).where(
                    models.Attribute.school_id == school_id,
                    models.Attribute.name == attr_name,
                )
            )
            if attr:
                db.add(models.EvaluationRating(
                    evaluation_id=evaluation.id,
                    attribute_id=attr.id,
                    rating=rating,
                ))
                ratings.append(rating)

        if ratings:
            evaluation.final_grade = round(sum(ratings) / len(ratings))

        created += 1

    return created


def seed() -> None:
    load_dotenv()
    with SessionLocal() as db:
        school = db.scalar(select(models.School).where(models.School.name == "Default School"))
        if not school:
            school = models.School(name="Default School")
            db.add(school)
            db.flush()

        get_or_create_user(
            db,
            full_name="Mia Manager",
            username="mia_manager",
            email="manager@propel.local",
            password="Propel123!",
            role=models.UserRole.MANAGER,
            school_id=school.id,
        )
        get_or_create_user(
            db,
            full_name="Sam Supervisor",
            username="sam_supervisor",
            email="supervisor@propel.local",
            password="Propel123!",
            role=models.UserRole.SUPERVISOR,
            school_id=school.id,
        )
        get_or_create_user(
            db,
            full_name="Sarah Johnson",
            username="sarah_johnson",
            email="instructor@propel.local",
            password="Propel123!",
            role=models.UserRole.INSTRUCTOR,
            school_id=school.id,
        )
        get_or_create_user(
            db,
            full_name="Alex Rivera",
            username="alex_rivera",
            email="alex@propel.local",
            password="Propel123!",
            role=models.UserRole.INSTRUCTOR,
            school_id=school.id,
        )
        get_or_create_user(
            db,
            full_name="Jordan Lee",
            username="jordan_lee",
            email="jordan@propel.local",
            password="Propel123!",
            role=models.UserRole.INSTRUCTOR,
            school_id=school.id,
        )
        get_or_create_user(
            db,
            full_name="Casey Morgan",
            username="casey_morgan",
            email="casey@propel.local",
            password="Propel123!",
            role=models.UserRole.SUPERVISOR,
            school_id=school.id,
        )
        get_or_create_user(
            db,
            full_name="Taylor Brooks",
            username="taylor_brooks",
            email="taylor@propel.local",
            password="Propel123!",
            role=models.UserRole.SUPERVISOR,
            school_id=school.id,
        )

        seed_curriculum(db, school.id)
        db.commit()

        n = seed_sample_evaluations(db, school.id)
        db.commit()

    print("Seed complete.")
    print("Login credentials (password: Propel123!):")
    print("  mia_manager      (Manager    — Mia Manager)")
    print("  sam_supervisor   (Supervisor — Sam Supervisor)")
    print("  sarah_johnson    (Instructor — Sarah Johnson)")
    print("  alex_rivera      (Instructor — Alex Rivera)")
    print("  jordan_lee       (Instructor — Jordan Lee)")
    print("  casey_morgan     (Supervisor — Casey Morgan)")
    print("  taylor_brooks    (Supervisor — Taylor Brooks)")
    print(f"Curriculum: {len(CURRICULUM)} levels, "
          f"{sum(len(l['skills']) for l in CURRICULUM)} skills seeded.")
    print(f"Sample evaluations: {n} created.")


if __name__ == "__main__":
    seed()
