import React from 'react';
import { Link } from 'react-router-dom';
import { Compass } from 'lucide-react';
import { buttonVariants } from '../design/ui';

const NotFound: React.FC = () => (
  <section className="mx-auto flex max-w-xl flex-col items-center px-4 py-32 text-center">
    <div className="grid h-14 w-14 place-items-center rounded-full bg-surface-2 text-muted">
      <Compass className="h-6 w-6" aria-hidden />
    </div>
    <p className="mt-6 font-mono text-sm text-accent">404</p>
    <h1 className="mt-2 text-3xl font-semibold tracking-tight text-text">This page does not exist</h1>
    <p className="mt-3 text-muted">The link may be old. Old console links that started with “#/” are redirected automatically.</p>
    <div className="mt-8 flex gap-3">
      <Link to="/" className={buttonVariants({ variant: 'secondary' })}>
        Home
      </Link>
      <Link to="/app" className={buttonVariants()}>
        Open console
      </Link>
    </div>
  </section>
);

export default NotFound;
