# React 规范

1. Prefer pure function components
2. For complex business logic, use hook injection pattern:
   - Each UI component has a corresponding hook (e.g., `UserList` ↔ `useUserList`)
   - Hooks are injected from outside via a `hook` prop
   - Hooks are composable with each other
