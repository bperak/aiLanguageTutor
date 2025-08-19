export default function Home() {
  return (
    <div className="min-h-[calc(100vh-56px)] grid place-items-center p-8">
      <div className="text-center max-w-xl">
        <h1 className="text-4xl font-semibold tracking-tight">Learn languages with your AI tutor</h1>
        <p className="text-muted-foreground mt-3">Personalized, simple, and effective. Start with Japanese today.</p>
        <div className="mt-6 flex items-center justify-center gap-4">
          <a className="px-5 py-2 rounded-md bg-black text-white hover:opacity-90" href="/register">Get started</a>
          <a className="px-5 py-2 rounded-md border hover:bg-slate-50" href="/login">I already have an account</a>
        </div>
      </div>
    </div>
  )
}
