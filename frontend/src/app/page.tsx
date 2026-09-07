import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-white">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b border-gray-200 bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded bg-navy-800 flex items-center justify-center text-white font-bold text-xl">R</div>
            <span className="text-xl font-bold tracking-tight text-navy-900">RegPulse</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/login" className="text-sm font-medium text-gray-600 hover:text-navy-900 transition-colors">
              Sign in
            </Link>
            <Link
              href="/register"
              className="rounded-lg bg-navy-800 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-navy-900 shadow-sm"
            >
              Get Started
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden bg-navy-900 pt-24 pb-32 text-center sm:pt-32 sm:pb-40 lg:pt-40 lg:pb-48">
          <div className="absolute inset-0 bg-[url('/bg-grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]"></div>
          <div className="relative mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <h1 className="mx-auto max-w-4xl font-display text-5xl font-extrabold tracking-tight text-white sm:text-7xl">
              RBI Regulatory Intelligence, <span className="text-blue-400">Instantly.</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg tracking-tight text-slate-300 sm:text-xl">
              Stop digging through thousands of PDFs. RegPulse uses advanced AI to deliver precise, cited answers to your complex compliance questions directly from the RBI&apos;s own circulars.
            </p>
            <div className="mt-10 flex justify-center gap-4">
              <Link
                href="/register"
                className="rounded-full bg-blue-500 px-8 py-3.5 text-sm font-semibold text-white shadow-sm hover:bg-blue-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-400 transition-all"
              >
                Start for Free
              </Link>
              <Link
                href="/library"
                className="rounded-full bg-slate-800 px-8 py-3.5 text-sm font-semibold text-white hover:bg-slate-700 transition-all border border-slate-700"
              >
                Browse Circulars
              </Link>
            </div>
          </div>
        </section>

        {/* Feature Section */}
        <section className="bg-slate-50 py-24 sm:py-32">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="mx-auto max-w-2xl sm:text-center">
              <h2 className="text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">Everything you need to stay compliant</h2>
              <p className="mt-6 text-lg leading-8 text-gray-600">
                Built strictly for financial institutions. We prioritize zero-hallucination factual extraction over predictive generation.
              </p>
            </div>
            <div className="mx-auto mt-16 max-w-5xl sm:mt-20 lg:mt-24 lg:max-w-none">
              <dl className="grid max-w-xl grid-cols-1 gap-x-8 gap-y-16 lg:max-w-none lg:grid-cols-3">
                <div className="flex flex-col">
                  <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                    <svg className="h-5 w-5 flex-none text-blue-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fillRule="evenodd" d="M10 1a4.5 4.5 0 00-4.5 4.5V9H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-.5V5.5A4.5 4.5 0 0010 1zm3 8V5.5a3 3 0 10-6 0V9h6z" clipRule="evenodd" />
                    </svg>
                    Zero Hallucination
                  </dt>
                  <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                    <p className="flex-auto">Our RAG pipelines guarantee strict citation-mapping. If the answer isn&apos;t in an RBI circular, the AI will explicitly ask you to consult an expert, averting regulatory risk.</p>
                  </dd>
                </div>
                <div className="flex flex-col">
                  <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                    <svg className="h-5 w-5 flex-none text-blue-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path fillRule="evenodd" d="M15.312 11.424a5.5 5.5 0 01-9.201 2.466l-.312-.311h2.433a.75.75 0 000-1.5H3.989a.75.75 0 00-.75.75v4.242a.75.75 0 001.5 0v-2.43l.31.31a7 7 0 0011.712-3.138.75.75 0 00-1.449-.39zm1.23-3.723a.75.75 0 00.219-.53V2.929a.75.75 0 00-1.5 0V5.36l-.31-.31A7 7 0 003.239 8.188a.75.75 0 101.448.389A5.5 5.5 0 0113.89 6.11l.311.31h-2.432a.75.75 0 000 1.5h4.243a.75.75 0 00.53-.219z" clipRule="evenodd" />
                    </svg>
                    Daily Sync
                  </dt>
                  <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                    <p className="flex-auto">Our specialized Celery workers index changes from the RBI website daily. We automatically track superseded documents to assure you refer to the active law.</p>
                  </dd>
                </div>
                <div className="flex flex-col">
                  <dt className="flex items-center gap-x-3 text-base font-semibold leading-7 text-gray-900">
                    <svg className="h-5 w-5 flex-none text-blue-600" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                      <path d="M10 12.5a2.5 2.5 0 100-5 2.5 2.5 0 000 5z" />
                      <path fillRule="evenodd" d="M.664 10.59a1.651 1.651 0 010-1.186A10.004 10.004 0 0110 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0110 17c-4.257 0-7.893-2.66-9.336-6.41zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                    </svg>
                    Action Items mapping
                  </dt>
                  <dd className="mt-4 flex flex-auto flex-col text-base leading-7 text-gray-600">
                    <p className="flex-auto">Interpretations are instantly mapped to actionable items tagged for internal teams (Compliance, Risk, IT). Extract, attribute, and execute smoothly.</p>
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-100 py-12">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center sm:text-left">
          <div className="flex flex-col sm:flex-row justify-between items-center">
            <div className="flex items-center gap-2 text-navy-900 font-bold tracking-tight">
              <div className="h-6 w-6 rounded bg-navy-800 flex items-center justify-center text-white text-xs">R</div>
              RegPulse
            </div>
            <p className="mt-4 sm:mt-0 text-sm leading-5 text-gray-500">
              &copy; {new Date().getFullYear()} RegPulse, Inc. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
