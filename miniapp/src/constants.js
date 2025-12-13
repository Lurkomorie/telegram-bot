/**
 * Constants for character creation
 * Attribute options for dropdowns
 */

export const RACE_TYPES = [
  // Row 1: Human races
  { value: "european", label: "European", image: "/assets/type-caucasian-1.webp" },
  { value: "asian", label: "Asian", image: "/assets/type-asian-1.webp" },
  { value: "african", label: "African", image: "/assets/type-african-1.webp" },
  { value: "latin", label: "Latin American", image: "/assets/type-latin-american-1.webp" },
  // Row 2: Fantasy races
  { value: "elf", label: "Elf", image: "/assets/type-elf-1.webp" },
  { value: "catgirl", label: "Catgirl", image: "/assets/type-beastfolk-1.webp" },
  { value: "succubus", label: "Succubus", image: "/assets/type-demon-1.webp" },
];

export const HAIR_COLORS = [
  { value: "brown", label: "Brunette", emoji: "🟤" },
  { value: "blonde", label: "Blonde", emoji: "🟡" },
  { value: "black", label: "Black", emoji: "⚫" },
  { value: "red", label: "Redhead", emoji: "🔴" },
  { value: "pink", label: "Pink", emoji: "🩷" },
  { value: "white", label: "White", emoji: "⚪" },
  { value: "blue", label: "Blue", emoji: "🔵" },
  { value: "green", label: "Green", emoji: "🟢" },
  { value: "purple", label: "Purple", emoji: "🟣" },
  { value: "multicolor", label: "Multicolor", emoji: "🌈" },
];

export const HAIR_STYLES = [
  { value: "long_straight", label: "Long Straight", icon: "/assets/long-straight.webp" },
  { value: "long_wavy", label: "Long Wavy", icon: "/assets/long-wavy.webp" },
  { value: "short", label: "Short", icon: "/assets/short.webp" },
  { value: "ponytail", label: "Ponytail", icon: "/assets/ponytail.webp" },
  { value: "braided", label: "Braided", icon: "/assets/braided.webp" },
  { value: "curly", label: "Curly", icon: "/assets/curly.webp" },
];

export const EYE_COLORS = [
  { value: "brown", label: "Brown", emoji: "🟤" },
  { value: "blue", label: "Blue", emoji: "🔵" },
  { value: "green", label: "Green", emoji: "🟢" },
  { value: "hazel", label: "Hazel", emoji: "🟡" },
  { value: "gray", label: "Gray", emoji: "⚫" },
];

export const BODY_TYPES = [
  { value: "slim", label: "Slim", image: "/assets/body-slim.webp" },
  { value: "athletic", label: "Athletic", image: "/assets/body-athletic.webp" },
  { value: "curvy", label: "Curvy", image: "/assets/body-curvy.webp" },
  { value: "voluptuous", label: "Voluptuous", image: "/assets/body-voluptuous.webp" },
];

export const BREAST_SIZES = [
  { value: "small", label: "Small" },
  { value: "medium", label: "Medium" },
  { value: "large", label: "Large" },
];

export const BUTT_SIZES = [
  { value: "small", label: "Small" },
  { value: "medium", label: "Medium" },
  { value: "large", label: "Large" },
];

// Voice options for character creation
// NOTE: Replace voice IDs with actual ElevenLabs voice IDs
// Preview files should be placed in miniapp/public/assets/voices/
export const VOICE_OPTIONS = [
  { 
    value: "BpjGufoPiobT79j2vtj4",  // Priyanka (default)
    labelKey: "softGentle",
    preview: "/assets/voices/soft-gentle.mp3"
  },
  { 
    value: "voice_playful_id",  // TODO: Replace with actual voice ID
    labelKey: "playfulFlirty",
    preview: "/assets/voices/playful-flirty.mp3"
  },
  { 
    value: "voice_confident_id",  // TODO: Replace with actual voice ID
    labelKey: "confidentBold",
    preview: "/assets/voices/confident-bold.mp3"
  },
  { 
    value: "voice_sweet_id",  // TODO: Replace with actual voice ID
    labelKey: "sweetInnocent",
    preview: "/assets/voices/sweet-innocent.mp3"
  },
];

