export function PlaceholderPage({ title, description }: { title: string; description: string }) {
  return (
    <section
      className='max-w-3xl rounded-[var(--radius-surface)] bg-[var(--surface-secondary)] px-5 py-6 sm:px-6'
      aria-labelledby='placeholder-title'
    >
      <h2 className='text-lg font-semibold text-[var(--text-primary)]' id='placeholder-title'>
        {title}
      </h2>
      <p className='mt-2 text-sm leading-6 text-[var(--text-secondary)]'>{description}</p>
    </section>
  )
}
