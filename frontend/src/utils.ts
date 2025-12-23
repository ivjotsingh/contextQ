// Simple utility to throttle function calls
// Used to reduce re-renders during streaming

export function throttle<T extends (...args: any[]) => any>(
    func: T,
    wait: number
): (...args: Parameters<T>) => void {
    let timeout: NodeJS.Timeout | null = null;
    let lastArgs: Parameters<T> | null = null;

    return function throttled(...args: Parameters<T>) {
        lastArgs = args;

        if (!timeout) {
            timeout = setTimeout(() => {
                if (lastArgs) {
                    func(...lastArgs);
                }
                timeout = null;
            }, wait);
        }
    };
}

// Simple debounce utility
export function debounce<T extends (...args: any[]) => any>(
    func: T,
    wait: number
): (...args: Parameters<T>) => void {
    let timeout: NodeJS.Timeout | null = null;

    return function debounced(...args: Parameters<T>) {
        if (timeout) {
            clearTimeout(timeout);
        }

        timeout = setTimeout(() => {
            func(...args);
        }, wait);
    };
}
