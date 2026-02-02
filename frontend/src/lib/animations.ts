/**
 * Animações Framer Motion para o Portal do Agente
 * Definições centralizadas para consistência visual
 */

// ============ Page Transitions ============
export const pageVariants = {
    initial: { opacity: 0, y: 20 },
    animate: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.4, ease: "easeOut" }
    },
    exit: {
        opacity: 0,
        y: -20,
        transition: { duration: 0.3 }
    }
};

// ============ Stagger Children ============
export const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
        opacity: 1,
        transition: {
            staggerChildren: 0.1,
            delayChildren: 0.2
        }
    }
};

export const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.4, ease: "easeOut" }
    }
};

// ============ Card Animations ============
export const cardHover = {
    scale: 1.02,
    y: -4,
    transition: { duration: 0.2, ease: "easeOut" }
};

export const cardTap = {
    scale: 0.98
};

// ============ Fade In ============
export const fadeIn = {
    initial: { opacity: 0 },
    animate: { opacity: 1, transition: { duration: 0.5 } },
    exit: { opacity: 0 }
};

// ============ Slide Up ============
export const slideUp = {
    initial: { opacity: 0, y: 40 },
    animate: {
        opacity: 1,
        y: 0,
        transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] }
    }
};

// ============ Scale In ============
export const scaleIn = {
    initial: { opacity: 0, scale: 0.9 },
    animate: {
        opacity: 1,
        scale: 1,
        transition: { duration: 0.4, ease: "easeOut" }
    }
};

// ============ Glassmorphism Glow ============
export const glowPulse = {
    animate: {
        boxShadow: [
            "0 0 20px rgba(var(--primary-rgb), 0.1)",
            "0 0 40px rgba(var(--primary-rgb), 0.2)",
            "0 0 20px rgba(var(--primary-rgb), 0.1)"
        ],
        transition: {
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
        }
    }
};

// ============ Skeleton Loader ============
export const shimmer = {
    animate: {
        backgroundPosition: ["200% 0", "-200% 0"],
        transition: {
            duration: 1.5,
            repeat: Infinity,
            ease: "linear"
        }
    }
};

// ============ Button Press ============
export const buttonPress = {
    whileHover: { scale: 1.02 },
    whileTap: { scale: 0.98 },
    transition: { duration: 0.1 }
};

// ============ Toast Notification ============
export const toastVariants = {
    initial: { opacity: 0, x: 100, scale: 0.9 },
    animate: {
        opacity: 1,
        x: 0,
        scale: 1,
        transition: { type: "spring", stiffness: 500, damping: 30 }
    },
    exit: {
        opacity: 0,
        x: 100,
        transition: { duration: 0.2 }
    }
};

// ============ Modal/Dialog ============
export const modalOverlay = {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 }
};

export const modalContent = {
    initial: { opacity: 0, scale: 0.95, y: 20 },
    animate: {
        opacity: 1,
        scale: 1,
        y: 0,
        transition: { type: "spring", stiffness: 300, damping: 25 }
    },
    exit: {
        opacity: 0,
        scale: 0.95,
        transition: { duration: 0.2 }
    }
};

// ============ List Item ============
export const listItem = {
    initial: { opacity: 0, x: -20 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 20 },
    transition: { duration: 0.3 }
};

// ============ Kanban Card Drag ============
export const kanbanCardDrag = {
    whileDrag: {
        scale: 1.05,
        rotate: 2,
        boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
        cursor: "grabbing"
    }
};

// ============ Status Indicator ============
export const statusPulse = {
    animate: {
        scale: [1, 1.2, 1],
        opacity: [1, 0.7, 1],
        transition: {
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut"
        }
    }
};
