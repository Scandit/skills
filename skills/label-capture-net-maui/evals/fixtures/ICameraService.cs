namespace MyApp.Services;

public interface ICameraService
{
    Task PauseFrameSourceAsync();
    Task ResumeFrameSourceAsync();
}
