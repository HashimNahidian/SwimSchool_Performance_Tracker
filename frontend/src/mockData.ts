import type { EvaluationSummary, Level, Skill, User } from "./types";

export const DEMO_USERS: User[] = [
  { id: 101, name: "Sarah Johnson", email: "sarah.j@propelswim.com", role: "INSTRUCTOR", active: true },
  { id: 102, name: "Mike Chen", email: "mike.c@propelswim.com", role: "INSTRUCTOR", active: true },
  { id: 103, name: "Emma Davis", email: "emma.d@propelswim.com", role: "INSTRUCTOR", active: true },
  { id: 201, name: "Tom Wilson", email: "tom.w@propelswim.com", role: "SUPERVISOR", active: true },
  { id: 202, name: "Lisa Park", email: "lisa.p@propelswim.com", role: "SUPERVISOR", active: true },
  { id: 301, name: "Alex Rivera", email: "alex.r@propelswim.com", role: "MANAGER", active: true },
];

export const DEMO_LEVELS: Level[] = [
  { id: 1, name: "Level 1 — Beginner", active: true },
  { id: 2, name: "Level 2 — Intermediate", active: true },
  { id: 3, name: "Level 3 — Advanced", active: true },
  { id: 4, name: "Level 4 — Competitive", active: true },
];

export const DEMO_SKILLS: Skill[] = [
  { id: 1, level_id: 1, name: "Freestyle", description: "Basic freestyle stroke technique", active: true },
  { id: 2, level_id: 1, name: "Water Safety", description: "Basic water safety fundamentals", active: true },
  { id: 3, level_id: 2, name: "Backstroke", description: "Backstroke form and technique", active: true },
  { id: 4, level_id: 2, name: "Breaststroke", description: "Breaststroke technique and timing", active: true },
  { id: 5, level_id: 3, name: "Butterfly", description: "Butterfly stroke body undulation", active: true },
  { id: 6, level_id: 3, name: "Turns & Starts", description: "Flip turns and racing dives", active: true },
  { id: 7, level_id: 4, name: "Race Strategy", description: "Competitive pacing and race tactics", active: true },
  { id: 8, level_id: 4, name: "Endurance Training", description: "Distance conditioning and sets", active: true },
];

export const DEMO_EVALUATIONS: EvaluationSummary[] = [
  // Sarah Johnson (instructor_id: 101) — supervised by Tom Wilson & Lisa Park
  { id: 1,  instructor_id: 101, instructor_name: "Sarah Johnson", supervisor_id: 201, supervisor_name: "Tom Wilson", level_id: 1, level_name: "Level 1 — Beginner",      skill_id: 1, skill_name: "Freestyle",         session_label: "Morning Lanes A",      session_date: "2026-01-06", status: "SUBMITTED", submitted_at: "2026-01-06T10:30:00Z" },
  { id: 2,  instructor_id: 101, instructor_name: "Sarah Johnson", supervisor_id: 201, supervisor_name: "Tom Wilson", level_id: 2, level_name: "Level 2 — Intermediate", skill_id: 3, skill_name: "Backstroke",        session_label: "Afternoon Session B",  session_date: "2026-01-13", status: "SUBMITTED", submitted_at: "2026-01-13T15:00:00Z" },
  { id: 3,  instructor_id: 101, instructor_name: "Sarah Johnson", supervisor_id: 202, supervisor_name: "Lisa Park",  level_id: 1, level_name: "Level 1 — Beginner",      skill_id: 2, skill_name: "Water Safety",      session_label: "Safety Review",        session_date: "2026-01-20", status: "SUBMITTED", submitted_at: "2026-01-20T11:00:00Z" },
  { id: 4,  instructor_id: 101, instructor_name: "Sarah Johnson", supervisor_id: 201, supervisor_name: "Tom Wilson", level_id: 3, level_name: "Level 3 — Advanced",      skill_id: 5, skill_name: "Butterfly",        session_label: "Advanced Class",       session_date: "2026-02-03", status: "SUBMITTED", submitted_at: "2026-02-03T09:00:00Z" },
  { id: 5,  instructor_id: 101, instructor_name: "Sarah Johnson", supervisor_id: 202, supervisor_name: "Lisa Park",  level_id: 2, level_name: "Level 2 — Intermediate", skill_id: 4, skill_name: "Breaststroke",     session_label: "Breaststroke Clinic",  session_date: "2026-02-17", status: "SUBMITTED", submitted_at: "2026-02-17T14:00:00Z" },
  { id: 6,  instructor_id: 101, instructor_name: "Sarah Johnson", supervisor_id: 201, supervisor_name: "Tom Wilson", level_id: 3, level_name: "Level 3 — Advanced",      skill_id: 6, skill_name: "Turns & Starts",  session_label: "Technique Block",      session_date: "2026-03-01", status: "DRAFT",      submitted_at: null },

  // Mike Chen (instructor_id: 102) — supervised by Tom Wilson & Lisa Park
  { id: 7,  instructor_id: 102, instructor_name: "Mike Chen",     supervisor_id: 201, supervisor_name: "Tom Wilson", level_id: 4, level_name: "Level 4 — Competitive", skill_id: 7, skill_name: "Race Strategy",    session_label: "Competition Prep",     session_date: "2026-01-08", status: "SUBMITTED", submitted_at: "2026-01-08T14:00:00Z" },
  { id: 8,  instructor_id: 102, instructor_name: "Mike Chen",     supervisor_id: 202, supervisor_name: "Lisa Park",  level_id: 3, level_name: "Level 3 — Advanced",      skill_id: 6, skill_name: "Turns & Starts",  session_label: "Technique Session",    session_date: "2026-01-15", status: "SUBMITTED", submitted_at: "2026-01-15T09:30:00Z" },
  { id: 9,  instructor_id: 102, instructor_name: "Mike Chen",     supervisor_id: 201, supervisor_name: "Tom Wilson", level_id: 4, level_name: "Level 4 — Competitive", skill_id: 8, skill_name: "Endurance Training", session_label: "Endurance Block",      session_date: "2026-02-05", status: "SUBMITTED", submitted_at: "2026-02-05T16:00:00Z" },
  { id: 10, instructor_id: 102, instructor_name: "Mike Chen",     supervisor_id: 202, supervisor_name: "Lisa Park",  level_id: 2, level_name: "Level 2 — Intermediate", skill_id: 3, skill_name: "Backstroke",        session_label: "Backstroke Workshop",  session_date: "2026-02-19", status: "SUBMITTED", submitted_at: "2026-02-19T10:00:00Z" },
  { id: 11, instructor_id: 102, instructor_name: "Mike Chen",     supervisor_id: 201, supervisor_name: "Tom Wilson", level_id: 4, level_name: "Level 4 — Competitive", skill_id: 7, skill_name: "Race Strategy",    session_label: "Sprint Drills",        session_date: "2026-03-01", status: "DRAFT",      submitted_at: null },

  // Emma Davis (instructor_id: 103) — supervised by Lisa Park & Tom Wilson
  { id: 12, instructor_id: 103, instructor_name: "Emma Davis",    supervisor_id: 202, supervisor_name: "Lisa Park",  level_id: 1, level_name: "Level 1 — Beginner",      skill_id: 1, skill_name: "Freestyle",         session_label: "Beginner Intro",       session_date: "2026-01-05", status: "SUBMITTED", submitted_at: "2026-01-05T10:00:00Z" },
  { id: 13, instructor_id: 103, instructor_name: "Emma Davis",    supervisor_id: 201, supervisor_name: "Tom Wilson", level_id: 1, level_name: "Level 1 — Beginner",      skill_id: 2, skill_name: "Water Safety",      session_label: "Water Safety 101",     session_date: "2026-01-12", status: "SUBMITTED", submitted_at: "2026-01-12T11:30:00Z" },
  { id: 14, instructor_id: 103, instructor_name: "Emma Davis",    supervisor_id: 202, supervisor_name: "Lisa Park",  level_id: 2, level_name: "Level 2 — Intermediate", skill_id: 4, skill_name: "Breaststroke",     session_label: "Stroke Refinement",    session_date: "2026-01-26", status: "SUBMITTED", submitted_at: "2026-01-26T14:30:00Z" },
  { id: 15, instructor_id: 103, instructor_name: "Emma Davis",    supervisor_id: 201, supervisor_name: "Tom Wilson", level_id: 2, level_name: "Level 2 — Intermediate", skill_id: 3, skill_name: "Backstroke",        session_label: "Backstroke Basics",    session_date: "2026-02-09", status: "SUBMITTED", submitted_at: "2026-02-09T09:00:00Z" },
  { id: 16, instructor_id: 103, instructor_name: "Emma Davis",    supervisor_id: 202, supervisor_name: "Lisa Park",  level_id: 3, level_name: "Level 3 — Advanced",      skill_id: 5, skill_name: "Butterfly",        session_label: "Butterfly Workshop",   session_date: "2026-02-23", status: "SUBMITTED", submitted_at: "2026-02-23T13:00:00Z" },
  { id: 17, instructor_id: 103, instructor_name: "Emma Davis",    supervisor_id: 201, supervisor_name: "Tom Wilson", level_id: 1, level_name: "Level 1 — Beginner",      skill_id: 1, skill_name: "Freestyle",         session_label: "Splash & Learn",       session_date: "2026-03-02", status: "DRAFT",      submitted_at: null },
];
