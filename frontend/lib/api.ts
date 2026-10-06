const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export interface Project {
  id: string;
  title: string;
  logline?: string;
  premise?: string;
  synopsis?: string;
  beat_sheet?: string; // JSON string
  act_structure?: string; // JSON string
  themes?: string; // JSON string
  conflicts?: string; // JSON string
  endings?: string; // JSON string
  screenplay_structure?: string; // JSON string {acts: [...]} -- Stage 2 output
  period?: string; // e.g. "India, 1965"
  board_legend_settings?: string; // JSON string -- Stage 8 board settings (BoardSettings)
  created_at: string;
  updated_at: string;
  scenes?: Scene[];
  characters?: Character[];
}


export interface Character {
  id: string;
  project_id: string;
  name: string;
  description?: string;
  traits?: string; // JSON string list
  age?: number;
  personality?: string;
  weakness?: string;
  motivation?: string;
  fear?: string;
  backstory?: string;
  reference_image_url?: string;
  relationships?: string; // JSON string structure
  reference_image_paths?: string; // JSON string list -- Stage 6 locked reference set
  locked_seed?: number;
  is_locked?: number; // 0/1
}


export interface Scene {
  id: string;
  project_id: string;
  scene_number: number;
  heading: string;
  raw_content?: string;
  parser_meta?: string;
  order: number;
  created_at: string;
  action_blocks?: ActionBlock[];
  dialogues?: Dialogue[];
  shots?: Shot[];
  // Stage 3 -- scene understanding
  int_ext?: string;
  location?: string;
  time_of_day?: string;
  characters_present?: string; // JSON string list[str]
  action_summary?: string;
  emotion?: string;
  conflict?: string;
  key_objects?: string; // JSON string list[str]
  visual_emphasis?: string;
  continuity_notes?: string;
}

export interface ActionBlock {
  id: string;
  scene_id: string;
  content: string;
  order: number;
}

export interface Dialogue {
  id: string;
  scene_id: string;
  character_name: string;
  content: string;
  order: number;
}

export interface Shot {
  id: string;
  scene_id: string;
  shot_number: number;
  shot_size?: string;
  angle?: string;
  movement?: string;
  lens?: string;
  lighting?: string;
  emotion?: string;
  color_palette?: string;
  visual_tip?: string;
  notes?: string;
  order: number;
  shooting_order?: number;
  location_order?: string;
  day_night?: string;
  duration?: number;
  status?: string;
  color_label?: string;
  created_at: string;
  updated_at: string;
  storyboard_frames?: StoryboardFrame[];
  // Stage 4/5 -- automatic shot division + cinematography plan
  shot_type?: string;
  reasoning?: string;
  camera_height?: string;
  framing?: string;
  composition_notes?: string;
  lighting_detail?: string; // JSON string
  contrast?: string;
  depth_of_field?: string;
  perspective_notes?: string;
  characters_in_shot?: string; // JSON string list[str]
  // Stage 8 -- production board sheet
  board_caption?: string;
  board_dialogue?: string;
  board_crop?: string; // JSON [l, t, r, b] in source pixels
  // Stage 9 -- continuity QA
  needs_review?: number; // 0/1
  continuity_score?: number;
}

export interface ProjectVersion {
  id: string;
  project_id: string;
  version_name: string;
  snapshot: string;
  created_at: string;
}

export interface CallSheet {
  id: string;
  project_id: string;
  date: string;
  call_time?: string;
  location?: string;
  notes?: string;
  created_at: string;
}

export interface BudgetItem {
  id: string;
  project_id: string;
  category: string;
  name: string;
  cost: number;
}

export interface CollaboratorComment {
  id: string;
  project_id: string;
  scene_id?: string;
  user_name: string;
  role: string;
  content: string;
  created_at: string;
}

export interface StoryboardFrame {
  id: string;
  shot_id: string;
  image_url?: string;
  prompt?: string;
  negative_prompt?: string;
  status: string;
  created_at: string;
}

/** Stage 8 board sheet text, stored as JSON in Project.board_legend_settings. */
export interface BoardSettings {
  title?: string;
  title_native?: string;
  title_roman?: string;
  title_sub?: string;
  subtitle?: string;
  period?: string;
  tagline?: string;
  tagline_translation?: string;
  postmark_ring?: string;
  postmark_center?: string;
  end_lines?: string[];
  end_translation?: string;
  signature?: string;
  signature_roman?: string;
  end_stamp?: string;
  cast_notes?: string[];
  credit?: string;
  legend?: Record<string, string[]>;
}

export interface Board {
  id: string;
  project_id: string;
  board_number: number;
  scene_range_start: number;
  scene_range_end: number;
  title?: string;
  length_label?: string;
  page_range_label?: string;
  output_image_path?: string;
  output_pdf_path?: string;
  created_at: string;
  updated_at: string;
}

export interface ContinuityCheckResult {
  shot_id: string;
  needs_review: boolean;
  flags: string[];
  identity_score?: number;
  color_distance?: number;
  regenerated: boolean;
}

function getAuthToken(): string | null {
  if (typeof window !== 'undefined') {
    const userStr = localStorage.getItem('70mm_firebase_user');
    if (userStr) {
      try {
        const userObj = JSON.parse(userStr);
        if (userObj?.token) return userObj.token;
      } catch {}
    }
  }
  return null;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE}${path}`;
  const token = getAuthToken();
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  };
  
  if (token) {
    (headers as any)['Authorization'] = `Bearer ${token}`;
  }
  
  const response = await fetch(url, {
    ...options,
    headers,
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `API error: ${response.status} ${response.statusText}`);
  }
  
  if (response.status === 204) {
    return null as T;
  }
  
  return response.json() as Promise<T>;
}

export const api = {
  // Projects
  getProjects: () => request<Project[]>('/projects/'),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (title: string, logline?: string) => 
    request<Project>('/projects/', {
      method: 'POST',
      body: JSON.stringify({ title, logline }),
    }),
  updateProject: (id: string, updates: Partial<Project>) => 
    request<Project>(`/projects/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    }),
  deleteProject: (id: string) => 
    request<void>(`/projects/${id}`, { method: 'DELETE' }),
  duplicateProject: (id: string) =>
    request<Project>(`/projects/${id}/duplicate`, {
      method: 'POST',
    }),
  structureProject: (id: string) =>
    request<Project>(`/projects/${id}/structure`, {
      method: 'POST',
    }),
  composeBoards: (id: string) =>
    request<Board[]>(`/projects/${id}/boards/compose`, {
      method: 'POST',
    }),
  
  uploadScript: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const token = getAuthToken();
    const headers: HeadersInit = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return fetch(`${API_BASE}/projects/${projectId}/parse`, {
      method: 'POST',
      body: formData,
      headers,
    }).then(res => {
      if (!res.ok) throw new Error('Failed parsing script');
      return res.json() as Promise<Project>;
    });
  },

  // Scenes
  getScenes: (projectId: string) => 
    request<Scene[]>(`/scenes/?project_id=${projectId}`),
  getScene: (id: string) => request<Scene>(`/scenes/${id}`),
  updateScene: (id: string, updates: Partial<Scene>) => 
    request<Scene>(`/scenes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    }),
  reorderScenes: (ids: string[]) =>
    request<void>('/scenes/reorder', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),
  understandScene: (id: string) =>
    request<Scene>(`/scenes/${id}/understand`, {
      method: 'POST',
    }),
  generateShotPlan: (sceneId: string) =>
    request<Shot[]>(`/scenes/${sceneId}/shots/generate-plan`, {
      method: 'POST',
    }),

  // Shots
  getShots: (sceneId: string) => 
    request<Shot[]>(`/shots/?scene_id=${sceneId}`),
  createShot: (sceneId: string, shot_number: number, notes?: string) => 
    request<Shot>(`/shots/?scene_id=${sceneId}`, {
      method: 'POST',
      body: JSON.stringify({ shot_number, notes }),
    }),
  updateShot: (id: string, shotData: Partial<Shot>) => 
    request<Shot>(`/shots/${id}`, {
      method: 'PUT',
      body: JSON.stringify(shotData),
    }),
  deleteShot: (id: string) => 
    request<void>(`/shots/${id}`, { method: 'DELETE' }),
  reorderShots: (ids: string[]) =>
    request<void>('/shots/reorder', {
      method: 'POST',
      body: JSON.stringify({ ids }),
    }),
  editShot: (id: string, instruction: string) =>
    request<Shot>(`/shots/${id}/edit`, {
      method: 'PATCH',
      body: JSON.stringify({ instruction }),
    }),
  checkShotContinuity: (id: string, reinforcedRegenerate: boolean = false) =>
    request<ContinuityCheckResult>(`/shots/${id}/continuity-check?reinforced_regenerate=${reinforcedRegenerate}`, {
      method: 'POST',
    }),

  // AI Engines
  generateStory: (projectId: string, idea: string) => 
    request<any>(`/ai/projects/${projectId}/generate-story`, {
      method: 'POST',
      body: JSON.stringify({ idea }),
    }),
  formulateScene: (sceneId: string, action_line: string) => 
    request<any>(`/ai/scenes/${sceneId}/formulate`, {
      method: 'POST',
      body: JSON.stringify({ action_line }),
    }),
  directorsMuse: (shotId: string, action_line: string, director_style: string = 'Standard') => 
    request<any>(`/ai/shots/${shotId}/muse`, {
      method: 'POST',
      body: JSON.stringify({ action_line, director_style }),
    }),
  getMuseHistory: (shotId: string) => 
    request<any[]>(`/shots/${shotId}/muse-history`),

  buildPrompt: (shotId: string) => 
    request<any>(`/ai/shots/${shotId}/prompt-builder`, {
      method: 'POST',
    }),

  // Storyboard
  generateStoryboard: (shotId: string) => 
    request<StoryboardFrame>(`/storyboards/${shotId}/generate`, {
      method: 'POST',
    }),
  getStoryboardFrames: (projectId: string) => 
    request<StoryboardFrame[]>(`/storyboards/project/${projectId}`),

  // Characters
  getCharacters: (projectId: string) => 
    request<Character[]>(`/characters/?project_id=${projectId}`),
  createCharacter: (projectId: string, name: string) => 
    request<Character>(`/characters/?project_id=${projectId}`, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  updateCharacter: (id: string, updates: Partial<Character>) => 
    request<Character>(`/characters/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updates),
    }),
  deleteCharacter: (id: string) =>
    request<void>(`/characters/${id}`, {
      method: 'DELETE',
    }),
  // Stage 6: pass 1-4 reference photos to lock user-supplied images, or no
  // files at all to auto-generate one with a fresh seed and freeze that seed.
  lockCharacterReference: async (id: string, files?: File[]) => {
    // Backend takes 4 named single-file params (file1..file4), not a
    // List[UploadFile] -- a confirmed fastapi 0.111.0 bug fails multipart
    // list validation regardless of file count. See characters.py.
    const trimmed = (files || []).slice(0, 4);
    const token = getAuthToken();
    const headers: HeadersInit = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    // No files -> send NO body at all, not an empty FormData. Verified
    // live: this fastapi/starlette version 400s with "There was an error
    // parsing the body" on a multipart/form-data request with zero actual
    // parts (python-multipart can't parse an empty multipart stream) --
    // omitting the body entirely sidesteps multipart parsing altogether
    // and correctly resolves all four File(None) params to None, which is
    // exactly the auto-generate-and-freeze-a-seed path this call wants.
    let body: FormData | undefined;
    if (trimmed.length > 0) {
      const formData = new FormData();
      trimmed.forEach((f, i) => formData.append(`file${i + 1}`, f));
      body = formData;
    }

    const res = await fetch(`${API_BASE}/characters/${id}/lock-reference`, {
      method: 'POST',
      body,
      headers,
    });
    if (!res.ok) {
      const errorText = await res.text();
      throw new Error(errorText || `Failed to lock character reference (${res.status})`);
    }
    return res.json() as Promise<Character>;
  },
  
  // Batch Shots
  batchUpdateShots: (ids: string[], updates: Partial<Shot>) =>
    request<Shot[]>('/shots/batch', {
      method: 'PUT',
      body: JSON.stringify({ ids, updates }),
    }),

  // Continuity
  validateContinuity: (sceneId: string) =>
    request<{ warnings: any[] }>(`/scenes/${sceneId}/validate-continuity`, {
      method: 'POST',
    }),

  // Production Versions
  getProjectVersions: (projectId: string) =>
    request<ProjectVersion[]>(`/projects/${projectId}/versions`),
  createProjectVersion: (projectId: string, version_name: string) =>
    request<ProjectVersion>(`/projects/${projectId}/versions`, {
      method: 'POST',
      body: JSON.stringify({ version_name }),
    }),
  restoreProjectVersion: (versionId: string) =>
    request<any>(`/versions/${versionId}/restore`, {
      method: 'POST',
    }),

  // Call Sheets
  getCallSheets: (projectId: string) =>
    request<CallSheet[]>(`/projects/${projectId}/callsheets`),
  createCallSheet: (projectId: string, data: { date: string; call_time?: string; location?: string; notes?: string }) =>
    request<CallSheet>(`/projects/${projectId}/callsheets`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deleteCallSheet: (id: string) =>
    request<void>(`/callsheets/${id}`, { method: 'DELETE' }),

  // Budgets
  getBudget: (projectId: string) =>
    request<BudgetItem[]>(`/projects/${projectId}/budget`),
  createBudgetItem: (projectId: string, category: string, name: string, cost: number) =>
    request<BudgetItem>(`/projects/${projectId}/budget`, {
      method: 'POST',
      body: JSON.stringify({ category, name, cost }),
    }),
  deleteBudgetItem: (id: string) =>
    request<void>(`/budget/${id}`, { method: 'DELETE' }),

  // Comments
  getComments: (projectId: string) =>
    request<CollaboratorComment[]>(`/projects/${projectId}/comments`),
  createComment: (projectId: string, commentData: { scene_id?: string; user_name: string; role?: string; content: string }) =>
    request<CollaboratorComment>(`/projects/${projectId}/comments`, {
      method: 'POST',
      body: JSON.stringify(commentData),
    }),
  deleteComment: (id: string) =>
    request<void>(`/comments/${id}`, { method: 'DELETE' }),

  // Cinematic RAG
  queryRAG: (query: string, projectId?: string) => {
    const formData = new FormData();
    formData.append('query', query);
    if (projectId) formData.append('project_id', projectId);
    
    const token = getAuthToken();
    const headers: HeadersInit = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    return fetch(`${API_BASE}/rag/query`, {
      method: 'POST',
      body: formData,
      headers,
    }).then(res => res.json() as Promise<{ results: any[] }>);
  },
  
  uploadRAGDocument: (projectId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', projectId);
    
    const token = getAuthToken();
    const headers: HeadersInit = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    
    return fetch(`${API_BASE}/rag/upload`, {
      method: 'POST',
      body: formData,
      headers,
    }).then(res => res.json());
  },
};

