export default function VortexLogo({ size = 24, className = '' }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      className={className}
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M5.5 9.5L22.4 52.8L31.9 38.4L20.6 24.1L32 30.3L43.4 24.1L32.1 38.4L41.6 52.8L58.5 9.5L43.7 17.4L32 11L20.3 17.4L5.5 9.5Z"
        fill="currentColor"
      />
      <path
        d="M18 14.2L31.9 21.9L46 14.2L39.9 30.3L32 34.7L24.1 30.3L18 14.2Z"
        fill="white"
        fillOpacity="0.32"
      />
      <path
        d="M12.4 13.8L23.5 42.1L30.1 32.1L24.7 24.9L32 28.9L39.3 24.9L33.9 32.1L40.5 42.1L51.6 13.8"
        stroke="currentColor"
        strokeWidth="3.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.55"
      />
    </svg>
  )
}
