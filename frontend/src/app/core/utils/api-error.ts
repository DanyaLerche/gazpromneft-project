export function getApiErrorMessage(error: any, fallback: string): string {
  const nestedMessage = error?.error?.error?.message;
  if (typeof nestedMessage === 'string' && nestedMessage.trim()) {
    return nestedMessage;
  }

  const detail = error?.error?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length) {
    const message = detail
      .map((item) => item?.msg || item?.message || '')
      .filter(Boolean)
      .join(', ');

    if (message) {
      return message;
    }
  }

  const message = error?.message;
  if (typeof message === 'string' && message.trim()) {
    return message;
  }

  return fallback;
}
